"""Create public download metadata from locally approved inference artifacts.

This utility hashes files; it does not retrieve DVC data or upload anything.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from urllib.parse import quote

from dermapred.inference.download import ModelArtifact, ModelRelease

DEFAULT_VERSION_PATH = Path(__file__).resolve().parents[1] / "VERSION"


def create_model_manifest(
    name: str,
    version: str | None,
    base_url: str,
    artifacts: dict[str, Path],
    output_path: Path,
    *,
    version_path: Path = DEFAULT_VERSION_PATH,
) -> None:
    """Write a pinned manifest for files that will be published at base_url.

    Args:
        name: Model identifier.
        version: Explicit model version, or None to read the project's VERSION file.
        base_url: Public HTTPS directory. ``{version}`` is replaced with the
            selected version, so GitHub tag URLs can follow bumpversion too.
        artifacts: Named local files, for example weights and calibrator.
        output_path: New JSON manifest to create; existing files are not overwritten.
        version_path: Version file to read when no explicit version is supplied.

    Raises:
        OSError: If an input cannot be read or output cannot be created.
        ValueError: If release fields or file names are invalid or ambiguous.
    """
    if version is None:
        version = version_path.read_text(encoding="utf-8").strip()
    if not version:
        raise ValueError("The model version must not be empty.")
    base_url = base_url.replace("{version}", version)
    files: dict[str, ModelArtifact] = {}
    filenames: set[str] = set()
    for role, path in artifacts.items():
        if path.name in filenames:
            raise ValueError("Release artifacts must have distinct filenames.")
        filenames.add(path.name)
        with path.open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
        files[role] = ModelArtifact(
            filename=path.name,
            url=f"{base_url.rstrip('/')}/{quote(path.name)}",
            sha256=digest,
            size_bytes=path.stat().st_size,
        )
    release = ModelRelease(name, version, files)
    data = {
        "schema_version": 1,
        "name": release.name,
        "version": release.version,
        "files": {
            role: {
                "filename": artifact.filename,
                "url": artifact.url,
                "sha256": artifact.sha256,
                "size_bytes": artifact.size_bytes,
            }
            for role, artifact in release.files.items()
        },
    }
    with output_path.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(data, indent=2) + "\n")


def main(arguments: Sequence[str] | None = None) -> int:
    """Create a manifest without publishing artifacts."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", required=True)
    version_options = parser.add_mutually_exclusive_group()
    version_options.add_argument(
        "--version", help="Override the project version for an independently versioned model."
    )
    version_options.add_argument(
        "--version-file",
        type=Path,
        default=DEFAULT_VERSION_PATH,
        help="Version file to read (default: the repository's VERSION file).",
    )
    parser.add_argument(
        "--base-url", required=True, help="Public HTTPS directory; supports {version}."
    )
    parser.add_argument("--artifact", required=True, action="append", metavar="ROLE=PATH")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(arguments)
    artifacts: dict[str, Path] = {}
    try:
        for specification in args.artifact:
            role, separator, path = specification.partition("=")
            if not separator or not path or role in artifacts:
                raise ValueError("Use distinct --artifact ROLE=PATH arguments.")
            artifacts[role] = Path(path)
        create_model_manifest(
            args.name,
            args.version,
            args.base_url,
            artifacts,
            args.output,
            version_path=args.version_file,
        )
    except (OSError, ValueError) as error:
        print(f"Manifest creation failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
