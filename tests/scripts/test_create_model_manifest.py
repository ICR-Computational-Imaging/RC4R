"""Ensure manifests and download URLs follow the project's version file."""

import json
from pathlib import Path

import pytest

from scripts import create_model_manifest as generator


@pytest.mark.parametrize("version", ["0.1.0", "0.2.0.dev4"])
def test_cli_reads_version_and_expands_release_url(tmp_path: Path, version: str) -> None:
    version_path = tmp_path / "VERSION"
    version_path.write_text(version + "\n")
    weights = tmp_path / "model.pt"
    weights.write_bytes(b"model weights")
    output = tmp_path / "manifest.json"
    result = generator.main(
        [
            "--name",
            "example",
            "--version-file",
            str(version_path),
            "--base-url",
            "https://example.org/releases/download/v{version}",
            "--artifact",
            f"weights={weights}",
            "--output",
            str(output),
        ]
    )
    assert result == 0
    manifest = json.loads(output.read_text())
    assert manifest["version"] == version
    assert manifest["files"]["weights"]["url"] == (
        f"https://example.org/releases/download/v{version}/model.pt"
    )


def test_cli_default_version_comes_from_repository_not_working_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    expected_version = generator.DEFAULT_VERSION_PATH.read_text().strip()
    monkeypatch.chdir(tmp_path)
    (tmp_path / "VERSION").write_text("999.0.0")
    (tmp_path / "model.pt").write_bytes(b"approved weights")
    assert (
        generator.main(
            [
                "--name",
                "example",
                "--base-url",
                "https://example.org/v{version}",
                "--artifact",
                "weights=model.pt",
                "--output",
                "manifest.json",
            ]
        )
        == 0
    )
    manifest = json.loads((tmp_path / "manifest.json").read_text())
    assert manifest["version"] == expected_version
    assert manifest["files"]["weights"]["url"] == (
        f"https://example.org/v{expected_version}/model.pt"
    )


def test_api_uses_new_version_after_bump(tmp_path: Path) -> None:
    version_path = tmp_path / "VERSION"
    weights = tmp_path / "model.pt"
    weights.write_bytes(b"unchanged approved model")
    manifests = []
    for version in ("0.1.0.dev3", "0.1.0"):
        version_path.write_text(version)
        output = tmp_path / f"{version}.json"
        generator.create_model_manifest(
            "example",
            None,
            "https://example.org/v{version}",
            {"weights": weights},
            output,
            version_path=version_path,
        )
        manifests.append(json.loads(output.read_text()))
    assert [manifest["version"] for manifest in manifests] == ["0.1.0.dev3", "0.1.0"]
    assert manifests[0]["files"]["weights"]["sha256"] == manifests[1]["files"]["weights"]["sha256"]
    assert manifests[1]["files"]["weights"]["url"] == "https://example.org/v0.1.0/model.pt"


def test_explicit_model_version_does_not_require_version_file(tmp_path: Path) -> None:
    weights = tmp_path / "model.pt"
    weights.write_bytes(b"approved model")
    output = tmp_path / "manifest.json"
    generator.create_model_manifest(
        "example",
        "1.2.0",
        "https://example.org/v{version}",
        {"weights": weights},
        output,
        version_path=tmp_path / "missing-VERSION",
    )
    manifest = json.loads(output.read_text())
    assert manifest["version"] == "1.2.0"
    assert manifest["files"]["weights"]["url"] == "https://example.org/v1.2.0/model.pt"


@pytest.mark.parametrize("version", [None, "\n", "../not-a-version"])
def test_cli_rejects_unavailable_or_invalid_version_file(
    tmp_path: Path, version: str | None, capsys: pytest.CaptureFixture[str]
) -> None:
    version_path = tmp_path / "VERSION"
    if version is not None:
        version_path.write_text(version)
    weights = tmp_path / "model.pt"
    weights.write_bytes(b"approved model")
    output = tmp_path / "manifest.json"
    assert (
        generator.main(
            [
                "--name",
                "example",
                "--version-file",
                str(version_path),
                "--base-url",
                "https://example.org/v{version}",
                "--artifact",
                f"weights={weights}",
                "--output",
                str(output),
            ]
        )
        == 1
    )
    assert "Manifest creation failed" in capsys.readouterr().err
    assert not output.exists()
