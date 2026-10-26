"""Fetch synthetic release metadata without contacting GitHub."""

import io
import json
from pathlib import Path
from typing import TypedDict
from urllib.error import URLError
from urllib.request import Request

import pytest

from dermapred.inference import download
from scripts.create_model_manifest import create_model_manifest


class ManifestOptions(TypedDict, total=False):
    repository: str
    version: str
    timeout: float


class Response(io.BytesIO):
    def geturl(self) -> str:
        return "https://release-assets.githubusercontent.com/manifest"


class Opener:
    def __init__(self, payload: bytes) -> None:
        self.payload = payload
        self.requests: list[str] = []

    def open(self, request: Request, timeout: float) -> Response:
        self.requests.append(request.full_url)
        return Response(self.payload)


@pytest.fixture
def remote_manifest(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Opener:
    weights = tmp_path / "weights.pt"
    calibrator = tmp_path / "calibrator.json"
    weights.write_bytes(b"synthetic weights")
    calibrator.write_bytes(b"synthetic calibrator")
    path = tmp_path / "manifest.json"
    create_model_manifest(
        "example",
        "1.0.0",
        "https://github.com/owner/project/releases/download/v1.0.0",
        {"weights": weights, "calibrator": calibrator},
        path,
    )
    opener = Opener(path.read_bytes())
    monkeypatch.setattr(download, "build_opener", lambda *args: opener)
    monkeypatch.setattr(download, "package_version", lambda name: "1.0.0")
    return opener


def test_installed_version_selects_exact_tag_and_caches_manifest(
    remote_manifest: Opener, tmp_path: Path
) -> None:
    cache = tmp_path / "cache"
    path = download.download_release_manifest(repository="owner/project", cache_dir=cache)
    assert path.read_bytes() == remote_manifest.payload
    assert remote_manifest.requests == [
        "https://github.com/owner/project/releases/download/v1.0.0/model-release.json"
    ]
    assert download.download_release_manifest(repository="owner/project", cache_dir=cache) == path
    assert (
        download.download_release_manifest(
            repository="owner/project", cache_dir=cache, offline=True
        )
        == path
    )
    assert len(remote_manifest.requests) == 1


def test_version_override_does_not_use_installed_version(
    remote_manifest: Opener, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(download, "package_version", lambda name: "2.0.0.dev3")
    path = download.download_release_manifest(
        repository="owner/project", version="1.0.0", cache_dir=tmp_path
    )
    assert download.ModelRelease.load(path).version == "1.0.0"


def test_missing_manifest_offline_never_uses_network(
    remote_manifest: Opener, tmp_path: Path
) -> None:
    with pytest.raises(FileNotFoundError, match="No valid cached manifest"):
        download.download_release_manifest(
            repository="owner/project", cache_dir=tmp_path, offline=True
        )
    assert remote_manifest.requests == []


def test_corrupt_manifest_is_rejected_offline_and_repaired(
    remote_manifest: Opener, tmp_path: Path
) -> None:
    path = download.download_release_manifest(repository="owner/project", cache_dir=tmp_path)
    path.write_text("invalid JSON")
    with pytest.raises(FileNotFoundError):
        download.download_release_manifest(
            repository="owner/project", cache_dir=tmp_path, offline=True
        )
    assert len(remote_manifest.requests) == 1
    repaired = download.download_release_manifest(repository="owner/project", cache_dir=tmp_path)
    assert repaired.read_bytes() == remote_manifest.payload
    assert len(remote_manifest.requests) == 2


@pytest.mark.parametrize("problem", ["version", "urls", "calibrator", "json", "size"])
def test_invalid_remote_manifest_is_never_cached(
    remote_manifest: Opener, tmp_path: Path, problem: str
) -> None:
    data = json.loads(remote_manifest.payload)
    if problem == "version":
        data["version"] = "2.0.0"
    elif problem == "urls":
        data["files"]["weights"]["url"] = "https://other.example/weights.pt"
    elif problem == "calibrator":
        del data["files"]["calibrator"]
    remote_manifest.payload = json.dumps(data).encode()
    if problem == "json":
        remote_manifest.payload = b"invalid JSON"
    elif problem == "size":
        remote_manifest.payload = b"x" * (download._MANIFEST_MAX_BYTES + 1)
    with pytest.raises(ValueError):
        download.download_release_manifest(repository="owner/project", cache_dir=tmp_path)
    assert not list(tmp_path.rglob("model-release.json"))
    assert not list(tmp_path.rglob("*.part"))


def test_missing_public_release_reports_tag_without_fallback(
    remote_manifest: Opener, tmp_path: Path
) -> None:
    from unittest.mock import patch

    with patch.object(remote_manifest, "open", side_effect=URLError("Not found")):
        with pytest.raises(OSError, match="owner/project v1.0.0"):
            download.download_release_manifest(repository="owner/project", cache_dir=tmp_path)
    assert not list(tmp_path.rglob("*.part"))


@pytest.mark.parametrize(
    "options",
    [
        {"repository": "../unsafe"},
        {"version": "../unsafe"},
        {"version": "v1.0.0"},
        {"timeout": 0},
    ],
)
def test_reject_invalid_settings_before_network(
    remote_manifest: Opener, tmp_path: Path, options: ManifestOptions
) -> None:
    with pytest.raises(ValueError):
        download.download_release_manifest(cache_dir=tmp_path, **options)
    assert remote_manifest.requests == []
