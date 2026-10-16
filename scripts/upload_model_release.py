"""Upload verified model files to a draft GitHub Release using ``gh``.

Run from the repository root after pushing the approved release tag:

    uv run python -m scripts.upload_model_release \
        --repo OWNER/REPO --manifest model-release.json \
        --artifact weights=results/trained_models/binary_classifier.pt \
        --artifact calibrator=results/calibration/probability_calibrator.json

Use ``--dry-run`` to check local files without contacting GitHub. This utility
never publishes a release, pushes a tag, retrains a model, or retrieves DVC data.
Authenticate separately with ``gh auth login`` before uploading.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Sequence
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlsplit

from dermapred.inference.download import ModelRelease

_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*\Z")


def _gh(arguments: Sequence[str]) -> str:
    """Invoke gh without a shell or interactive input; surface failed commands."""
    try:
        result = subprocess.run(
            ["gh", *arguments], capture_output=True, text=True, stdin=subprocess.DEVNULL
        )
    except FileNotFoundError as error:
        raise RuntimeError(
            "Install GitHub CLI (gh), then authenticate with gh auth login."
        ) from error
    if result.returncode:
        raise RuntimeError(
            f"GitHub command failed: {result.stderr.strip() or result.stdout.strip()}"
        )
    return result.stdout


def _release_metadata(repository: str, tag: str) -> dict[str, Any] | None:
    # The REST release-by-tag endpoint does not reliably find draft releases.
    # Authenticated, paginated release lists include the visible drafts.
    response = _gh(
        [
            "api",
            "--hostname",
            "github.com",
            "--paginate",
            "--slurp",
            f"repos/{repository}/releases?per_page=100",
        ]
    )
    pages = json.loads(response)
    if not isinstance(pages, list) or any(not isinstance(page, list) for page in pages):
        raise ValueError("GitHub returned an invalid paginated release list.")
    matches = [
        entry
        for page in pages
        for entry in page
        if isinstance(entry, dict) and entry.get("tag_name") == tag
    ]
    if not matches:
        return None
    if len(matches) != 1:
        raise ValueError("More than one release uses this tag; resolve the ambiguity on GitHub.")
    metadata = matches[0]
    if metadata.get("draft") is not True:
        raise ValueError("The release is already published; only draft releases can be modified.")
    return metadata


def _file_identity(path: Path) -> tuple[int, str]:
    with path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    return path.stat().st_size, digest


def _verify_remote_files(
    repository: str,
    tag: str,
    metadata: dict[str, Any],
    files: dict[str, Path],
    verification_directory: Path,
    *,
    require_all: bool = False,
) -> set[str]:
    """Compare existing attachments with the verified local snapshots."""
    assets = metadata.get("assets")
    if not isinstance(assets, list):
        raise ValueError("GitHub returned an invalid release asset list.")
    names = {
        asset["name"]
        for asset in assets
        if isinstance(asset, dict) and isinstance(asset.get("name"), str)
    }
    if require_all and not files.keys() <= names:
        raise ValueError("The draft is missing expected attachments; retry the upload command.")
    present = files.keys() & names
    if present:
        verification_directory.mkdir()
    for name in sorted(present):
        _gh(
            [
                "release",
                "download",
                tag,
                "--repo",
                f"github.com/{repository}",
                "--pattern",
                name,
                "--dir",
                str(verification_directory),
            ]
        )
        downloaded = verification_directory / name
        if _file_identity(downloaded) != _file_identity(files[name]):
            raise ValueError(
                f"Existing asset {name!r} differs from the approved local file; "
                "nothing will be overwritten."
            )
    return present


def upload_model_release(
    repository: str,
    manifest_path: Path,
    artifacts: dict[str, Path],
    *,
    dry_run: bool = False,
    notes_path: Path | None = None,
) -> str:
    """Verify an inference bundle and create or complete its draft release.

    Args:
        repository: Explicit GitHub.com repository in OWNER/REPO format.
        manifest_path: Reviewed model manifest; its version determines ``vVERSION``.
        artifacts: Local files keyed by the artifact roles in the manifest.
        dry_run: Validate local files and URLs without invoking gh.
        notes_path: Optional release notes file for a new draft. Otherwise ask
            GitHub to generate release notes. Existing draft notes are preserved.

    Returns:
        The draft release URL, or a local verification summary for a dry run.

    Raises:
        OSError: If local files cannot be read or staged.
        ValueError: If the manifest, files, URLs, or existing release do not match.
        RuntimeError: If gh is unavailable or a GitHub operation fails.

    Files are copied to temporary storage and checked before network access.
    Existing draft attachments are downloaded and compared byte-for-byte by
    size and SHA-256. New uploads are also downloaded and checked. Failures may
    leave a partial draft, which can be completed by retrying this command.
    """
    parts = repository.split("/")
    if len(parts) != 2 or not all(_NAME.fullmatch(part) for part in parts):
        raise ValueError("Use an explicit repository in OWNER/REPO format.")
    if not _NAME.fullmatch(manifest_path.name):
        raise ValueError("The manifest must have a simple filename without special characters.")

    with tempfile.TemporaryDirectory(prefix="dermapred-release-") as temporary:
        root = Path(temporary)
        manifest_snapshot = root / manifest_path.name
        manifest_snapshot.write_bytes(manifest_path.read_bytes())
        release = ModelRelease.load(manifest_snapshot)
        tag = f"v{release.version}"
        if artifacts.keys() != release.files.keys():
            raise ValueError("Supply exactly one --artifact ROLE=PATH for every manifest role.")
        files = {manifest_snapshot.name: manifest_snapshot}
        for role, artifact in release.files.items():
            expected_path = f"/{repository}/releases/download/{tag}/{quote(artifact.filename)}"
            url = urlsplit(artifact.url)
            if url.netloc != "github.com" or url.path != expected_path or url.query:
                raise ValueError(
                    f"The {role!r} URL must target {repository}, tag {tag}, "
                    f"and filename {artifact.filename}."
                )
            if artifact.filename in files:
                raise ValueError("Manifest and artifact filenames must all be distinct.")
            snapshot = root / artifact.filename
            shutil.copyfile(artifacts[role], snapshot)
            if _file_identity(snapshot) != (artifact.size_bytes, artifact.sha256):
                raise ValueError(f"Local {role!r} does not match the manifest's size and SHA-256.")
            files[artifact.filename] = snapshot
        notes_snapshot = None
        if notes_path is not None:
            # Keep notes separate from assets, even when their filenames match.
            notes_directory = root / "release-notes"
            notes_directory.mkdir()
            notes_snapshot = notes_directory / "notes.md"
            notes_snapshot.write_bytes(notes_path.read_bytes())
        if dry_run:
            return (
                f"Verified {len(files)} local files for {repository} {tag}. "
                "No GitHub requests made; remote tag and draft have not been checked."
            )

        # Do not let gh invent a tag from the repository's latest main commit.
        _gh(["api", "--hostname", "github.com", f"repos/{repository}/git/ref/tags/{tag}"])
        metadata = _release_metadata(repository, tag)
        present: set[str] = set()
        if metadata is not None:
            present = _verify_remote_files(
                repository, tag, metadata, files, root / "existing-assets"
            )
        else:
            command = [
                "release",
                "create",
                tag,
                "--repo",
                f"github.com/{repository}",
                "--draft",
                "--verify-tag",
                "--title",
                f"Release {tag}",
            ]
            if notes_snapshot is None:
                command.append("--generate-notes")
            else:
                command.extend(["--notes-file", str(notes_snapshot)])
            if ".dev" in release.version:
                command.append("--prerelease")
            _gh(command)
        missing = [str(path) for name, path in files.items() if name not in present]
        if missing:
            _gh(["release", "upload", tag, *missing, "--repo", f"github.com/{repository}"])
        metadata = _release_metadata(repository, tag)
        if metadata is None:
            raise RuntimeError("The draft release could not be found after uploading.")
        _verify_remote_files(
            repository, tag, metadata, files, root / "uploaded-assets", require_all=True
        )
        return str(metadata.get("html_url") or f"https://github.com/{repository}/releases")


def main(arguments: Sequence[str] | None = None) -> int:
    """Prepare a draft; never publish it."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True, help="GitHub.com OWNER/REPO")
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--artifact", required=True, action="append", metavar="ROLE=PATH")
    parser.add_argument(
        "--notes-file", type=Path,
        help="Use this notes file for a new draft; otherwise GitHub generates the notes.",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(arguments)
    try:
        artifacts: dict[str, Path] = {}
        for specification in args.artifact:
            role, separator, path = specification.partition("=")
            if not separator or not path or role in artifacts:
                raise ValueError("Use distinct --artifact ROLE=PATH arguments.")
            artifacts[role] = Path(path)
        result = upload_model_release(
            args.repo, args.manifest, artifacts, dry_run=args.dry_run, notes_path=args.notes_file
        )
    except (OSError, ValueError, RuntimeError) as error:
        print(f"Draft release preparation failed: {error}", file=sys.stderr)
        return 1
    if args.dry_run:
        print(result)
    else:
        print(
            f"Draft release prepared: {result}\n"
            "Review the draft on GitHub, then publish when approved."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
