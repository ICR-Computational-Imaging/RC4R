"""Download versioned inference artifacts without access to research storage.

Run ``python -m dermapred.inference.download --manifest model-release.json``
to download every file described by a trusted, local release manifest.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
from collections.abc import Sequence
from dataclasses import dataclass
from http.client import HTTPMessage
from pathlib import Path
from typing import IO
from urllib.error import URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

_IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*\Z")
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_CHUNK_SIZE = 1024 * 1024


def _validate_url(url: str) -> None:
    """Require HTTPS URLs without embedded credentials."""
    parts = urlsplit(url)
    if (
        parts.scheme != "https"
        or not parts.hostname
        or parts.username is not None
        or parts.password is not None
        or parts.fragment
    ):
        raise ValueError("Artifact URLs must use HTTPS without credentials or fragments.")


class _HTTPSRedirectHandler(HTTPRedirectHandler):
    """Validate redirects before another request is sent."""

    def redirect_request(
        self,
        req: Request,
        fp: IO[bytes],
        code: int,
        msg: str,
        headers: HTTPMessage,
        newurl: str,
    ) -> Request | None:
        _validate_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


@dataclass(frozen=True)
class ModelArtifact:
    """One release file, identified by URL, size, and expected SHA-256."""

    filename: str
    url: str
    sha256: str
    size_bytes: int

    def __post_init__(self) -> None:
        if not _IDENTIFIER.fullmatch(self.filename):
            raise ValueError("Artifact filenames must be simple filenames, without directories.")
        _validate_url(self.url)
        if not _SHA256.fullmatch(self.sha256):
            raise ValueError("sha256 must contain 64 lowercase hexadecimal characters.")
        if type(self.size_bytes) is not int or self.size_bytes <= 0:
            raise ValueError("size_bytes must be a positive integer.")


@dataclass(frozen=True)
class ModelRelease:
    """A pinned model release and its named inference artifacts."""

    name: str
    version: str
    files: dict[str, ModelArtifact]

    def __post_init__(self) -> None:
        if not _IDENTIFIER.fullmatch(self.name) or not _IDENTIFIER.fullmatch(self.version):
            raise ValueError("Model name and version must be simple identifiers.")
        if not self.files or any(not _IDENTIFIER.fullmatch(role) for role in self.files):
            raise ValueError("A release must contain files with simple role identifiers.")

    @classmethod
    def load(cls, manifest_path: Path) -> ModelRelease:
        """Read a schema-version-1 JSON manifest supplied with a release.

        Args:
            manifest_path: Trusted local JSON file containing ``schema_version``,
                ``name``, ``version``, and ``files``. Each named file contains
                ``filename``, ``url``, ``sha256``, and ``size_bytes``.

        Returns:
            A validated, versioned release specification.

        Raises:
            OSError: If the manifest cannot be read.
            ValueError: If JSON or the release specification is invalid.
        """
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or type(data.get("schema_version")) is not int:
            raise ValueError("Manifest must contain integer schema_version 1.")
        if data["schema_version"] != 1:
            raise ValueError("Unsupported manifest schema_version; expected 1.")
        if not isinstance(data.get("name"), str) or not isinstance(data.get("version"), str):
            raise ValueError("Manifest name and version must be strings.")
        entries = data.get("files")
        if not isinstance(entries, dict) or not entries:
            raise ValueError("Manifest files must be a non-empty object.")
        files: dict[str, ModelArtifact] = {}
        for role, entry in entries.items():
            if not isinstance(entry, dict):
                raise ValueError(f"Artifact {role!r} must be an object.")
            for field in ("filename", "url", "sha256"):
                if not isinstance(entry.get(field), str):
                    raise ValueError(f"Artifact {role!r} requires string {field}.")
            size = entry.get("size_bytes")
            if type(size) is not int or size <= 0:
                raise ValueError(f"Artifact {role!r} requires positive integer size_bytes.")
            files[role] = ModelArtifact(
                filename=entry["filename"],
                url=entry["url"],
                sha256=entry["sha256"],
                size_bytes=size,
            )
        return cls(data["name"], data["version"], files)


def default_cache_directory() -> Path:
    """Return the platform cache directory, respecting DERMAPRED_CACHE_DIR."""
    override = os.environ.get("DERMAPRED_CACHE_DIR")
    if override:
        return Path(override).expanduser()
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Caches" / "dermapred"
    if sys.platform == "win32":
        return (
            Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local")))
            / ("dermapred")
            / "Cache"
        )
    return Path(os.environ.get("XDG_CACHE_HOME", str(Path.home() / ".cache"))) / "dermapred"


def _matches_artifact(path: Path, artifact: ModelArtifact) -> bool:
    if not path.is_file() or path.stat().st_size != artifact.size_bytes:
        return False
    with path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    return digest == artifact.sha256


def _download_artifact(artifact: ModelArtifact, destination: Path, timeout: float) -> None:
    """Stream into a temporary file and promote only fully verified bytes."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=destination.parent, prefix=".download-", suffix=".part", delete=False
        ) as output:
            temporary_path = Path(output.name)
            request = Request(artifact.url, headers={"User-Agent": "dermapred-model-downloader"})
            opener = build_opener(_HTTPSRedirectHandler())
            digest = hashlib.sha256()
            size = 0
            with opener.open(request, timeout=timeout) as response:
                _validate_url(response.geturl())
                while chunk := response.read(_CHUNK_SIZE):
                    size += len(chunk)
                    if size > artifact.size_bytes:
                        raise ValueError(f"Download exceeds expected size: {artifact.filename}.")
                    output.write(chunk)
                    digest.update(chunk)
            if size != artifact.size_bytes or digest.hexdigest() != artifact.sha256:
                raise ValueError(
                    f"Download failed size or SHA-256 verification: {artifact.filename}."
                )
        temporary_path.replace(destination)
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def download_model(
    manifest_path: Path,
    *,
    cache_dir: Path | None = None,
    offline: bool = False,
    timeout: float = 30.0,
) -> dict[str, Path]:
    """Return verified local paths for every file in a model release.

    Existing cached files are checked on every call. Missing or corrupt files
    are downloaded again unless ``offline`` is true. Downloads never occur on
    import or package installation, and files are never deserialised here.

    Args:
        manifest_path: Trusted local model-release manifest.
        cache_dir: Cache root; defaults to the platform user cache directory.
        offline: Require valid cached files and make no network requests.
        timeout: Positive network timeout in seconds for individual blocking operations.

    Returns:
        Mapping of artifact roles, such as ``weights`` and ``calibrator``, to
        verified paths. Cache entries include the model version and file hash.

    Raises:
        FileNotFoundError: If offline mode lacks a valid cached artifact.
        OSError: If local files or network access fail.
        ValueError: If settings, the manifest, or downloaded bytes are invalid.
    """
    if not 0 < timeout < float("inf"):
        raise ValueError("timeout must be positive and finite.")
    release = ModelRelease.load(manifest_path)
    root = default_cache_directory() if cache_dir is None else cache_dir
    paths = {
        role: root / release.name / release.version / artifact.sha256 / artifact.filename
        for role, artifact in release.files.items()
    }
    # Check the entire bundle before returning anything, including in offline mode.
    for role, artifact in release.files.items():
        destination = paths[role]
        if _matches_artifact(destination, artifact):
            continue
        if offline:
            raise FileNotFoundError(
                f"No verified cached {role!r} for {release.name} {release.version}."
            )
        _download_artifact(artifact, destination, timeout)
    return paths


def main(arguments: Sequence[str] | None = None) -> int:
    """Download a release from the command line; report errors without loading it."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--cache-dir", type=Path)
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--timeout", type=float, default=30.0)
    args = parser.parse_args(arguments)
    try:
        paths = download_model(
            args.manifest, cache_dir=args.cache_dir, offline=args.offline, timeout=args.timeout
        )
    except (OSError, URLError, ValueError) as error:
        print(f"Model download failed: {error}", file=sys.stderr)
        return 1
    print(json.dumps({role: str(path) for role, path in paths.items()}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
