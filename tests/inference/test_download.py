"""Exercise integrity, caching, and offline behavior without network access."""

import hashlib
import io
import json
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request

import pytest

from dermapred.inference import download
from scripts.create_model_manifest import create_model_manifest


class FakeResponse(io.BytesIO):
    """A streaming HTTPS response."""

    def geturl(self) -> str:
        return "https://release-assets.example.org/model.pt"


class FakeOpener:
    """Record requests and serve controlled artifact bytes."""

    def __init__(self, payload: bytes) -> None:
        self.payload = payload
        self.calls = 0

    def open(self, request: Request, timeout: float) -> FakeResponse:
        self.calls += 1
        assert request.full_url.startswith("https://")
        assert timeout > 0
        return FakeResponse(self.payload)


def write_manifest(tmp_path: Path, payload: bytes = b"approved weights") -> Path:
    """Create a release using the same manifest generator maintainers use."""
    weights = tmp_path / "model.pt"
    weights.write_bytes(payload)
    manifest = tmp_path / "model-release.json"
    create_model_manifest(
        "example-model",
        "1.0.0",
        "https://example.org/releases/v1.0.0",
        {"weights": weights},
        manifest,
    )
    return manifest


def test_download_verifies_and_reuses_cache(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest = write_manifest(tmp_path)
    opener = FakeOpener(b"approved weights")
    monkeypatch.setattr(download, "build_opener", lambda *args: opener)
    paths = download.download_model(manifest, cache_dir=tmp_path / "cache")
    assert paths["weights"].read_bytes() == b"approved weights"
    assert hashlib.sha256(b"approved weights").hexdigest() in paths["weights"].parts
    assert download.download_model(manifest, cache_dir=tmp_path / "cache") == paths
    assert download.download_model(manifest, cache_dir=tmp_path / "cache", offline=True) == paths
    assert opener.calls == 1


def test_corrupt_cache_is_rejected_offline_and_repaired(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest = write_manifest(tmp_path)
    opener = FakeOpener(b"approved weights")
    monkeypatch.setattr(download, "build_opener", lambda *args: opener)
    paths = download.download_model(manifest, cache_dir=tmp_path / "cache")
    # Same length: verifying size alone would accept this corruption.
    paths["weights"].write_bytes(b"tampered weights")
    with pytest.raises(FileNotFoundError, match="No verified cached"):
        download.download_model(manifest, cache_dir=tmp_path / "cache", offline=True)
    assert opener.calls == 1
    download.download_model(manifest, cache_dir=tmp_path / "cache")
    assert paths["weights"].read_bytes() == b"approved weights"
    assert opener.calls == 2


def test_offline_missing_cache_never_opens_network(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest = write_manifest(tmp_path)
    opener = FakeOpener(b"approved weights")
    monkeypatch.setattr(download, "build_opener", lambda *args: opener)
    with pytest.raises(FileNotFoundError):
        download.download_model(manifest, cache_dir=tmp_path / "cache", offline=True)
    assert opener.calls == 0
    assert not (tmp_path / "cache").exists()


@pytest.mark.parametrize("payload", [b"short", b"tampered weights", b"far too many weight bytes"])
def test_invalid_download_is_not_cached(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, payload: bytes
) -> None:
    manifest = write_manifest(tmp_path)
    monkeypatch.setattr(download, "build_opener", lambda *args: FakeOpener(payload))
    cache = tmp_path / "cache"
    with pytest.raises(ValueError):
        download.download_model(manifest, cache_dir=cache)
    assert not list(cache.rglob("*.pt"))
    assert not list(cache.rglob("*.part"))


def test_interrupted_download_cleans_up(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    manifest = write_manifest(tmp_path)

    class InterruptedOpener:
        def open(self, request: Request, timeout: float) -> FakeResponse:
            raise URLError("connection interrupted")

    monkeypatch.setattr(download, "build_opener", lambda *args: InterruptedOpener())
    with pytest.raises(URLError):
        download.download_model(manifest, cache_dir=tmp_path / "cache")
    assert not list((tmp_path / "cache").rglob("*.part"))


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("filename", "../model.pt"),
        ("filename", "C:\\model.pt"),
        ("url", "http://example.org/model.pt"),
        ("url", "https://user:password@example.org/model.pt"),
        ("sha256", "not-a-hash"),
        ("size_bytes", True),
        ("size_bytes", 0),
    ],
)
def test_invalid_manifest_is_rejected(tmp_path: Path, field: str, value: str | int) -> None:
    manifest = write_manifest(tmp_path)
    data = json.loads(manifest.read_text())
    data["files"]["weights"][field] = value
    manifest.write_text(json.dumps(data))
    with pytest.raises(ValueError):
        download.download_model(manifest, cache_dir=tmp_path / "cache")
    assert not (tmp_path / "cache").exists()


def test_https_redirect_cannot_downgrade_transport() -> None:
    from http.client import HTTPMessage

    handler = download._HTTPSRedirectHandler()
    with pytest.raises(ValueError, match="HTTPS"):
        handler.redirect_request(
            Request("https://example.org/model.pt"),
            io.BytesIO(),
            302,
            "Found",
            HTTPMessage(),
            "http://example.org/model.pt",
        )


def test_cache_override(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("DERMAPRED_CACHE_DIR", str(tmp_path))
    assert download.default_cache_directory() == tmp_path


def test_cli_reports_verified_paths_and_offline_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    manifest = write_manifest(tmp_path)
    arguments = ["--manifest", str(manifest), "--cache-dir", str(tmp_path / "cache")]
    assert download.main([*arguments, "--offline"]) == 1
    assert "No verified cached" in capsys.readouterr().err
    monkeypatch.setattr(download, "build_opener", lambda *args: FakeOpener(b"approved weights"))
    assert download.main(arguments) == 0
    assert Path(json.loads(capsys.readouterr().out)["weights"]).is_file()


def test_matching_calibrator_is_downloaded_with_weights(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    weights = tmp_path / "weights.pt"
    calibrator = tmp_path / "calibrator.json"
    weights.write_bytes(b"bundle file")
    calibrator.write_bytes(b"bundle file")
    manifest = tmp_path / "bundle.json"
    create_model_manifest(
        "model",
        "1.0",
        "https://example.org/v1.0",
        {"weights": weights, "calibrator": calibrator},
        manifest,
    )
    monkeypatch.setattr(download, "build_opener", lambda *args: FakeOpener(b"bundle file"))
    paths = download.download_model(manifest, cache_dir=tmp_path / "cache")
    assert set(paths) == {"weights", "calibrator"}
    assert paths["weights"] != paths["calibrator"]


def test_manifest_generator_does_not_overwrite_release(tmp_path: Path) -> None:
    manifest = write_manifest(tmp_path)
    original = manifest.read_bytes()
    with pytest.raises(FileExistsError):
        create_model_manifest(
            "model",
            "2.0",
            "https://example.org/v2.0",
            {"weights": tmp_path / "model.pt"},
            manifest,
        )
    assert manifest.read_bytes() == original
