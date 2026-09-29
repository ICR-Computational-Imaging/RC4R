"""Tests for the DermaMNIST download utility."""

from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from scripts import download_dermapred


def test_download_dermapred_dataset_saves_all_splits(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The downloader should save the images and labels from every split."""
    calls: list[tuple[str, int, bool, Path]] = []

    def fake_dermamnist(*, split: str, size: int, download: bool, root: Path) -> object:
        split_number = {"train": 1, "val": 2, "test": 3}[split]
        calls.append((split, size, download, root))
        return SimpleNamespace(
            imgs=np.full((2, size, size, 3), split_number, dtype=np.uint8),
            labels=np.full((2, 1), split_number, dtype=np.uint8),
        )

    monkeypatch.setattr(download_dermapred, "DermaMNIST", fake_dermamnist)
    output_path = tmp_path / "nested" / "raw_data"

    download_dermapred.download_dermapred_dataset(output_path, size=64)

    assert [(split, size, download) for split, size, download, _ in calls] == [
        ("train", 64, True),
        ("val", 64, False),
        ("test", 64, False),
    ]
    assert len({root for *_, root in calls}) == 1

    expected_values = {"train": 1, "validation": 2, "test": 3}
    for split, expected_value in expected_values.items():
        images = np.load(output_path / f"{split}_images.npy")
        labels = np.load(output_path / f"{split}_labels.npy")
        assert images.shape == (2, 64, 64, 3)
        assert labels.shape == (2, 1)
        assert np.all(images == expected_value)
        assert np.all(labels == expected_value)


@pytest.mark.parametrize("size", [0, 32, 256])
def test_download_dermapred_dataset_rejects_unsupported_size(
    tmp_path: Path,
    size: int,
) -> None:
    """Unsupported image dimensions should fail before creating output."""
    output_path = tmp_path / "raw_data"

    with pytest.raises(ValueError, match=f"Invalid size: {size}"):
        download_dermapred.download_dermapred_dataset(output_path, size=size)

    assert not output_path.exists()


def test_main_reports_success(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The CLI should pass its arguments to the downloader."""
    calls: list[tuple[Path, int]] = []

    def fake_download(output_dir: str | Path, size: int) -> None:
        calls.append((Path(output_dir), size))

    monkeypatch.setattr(download_dermapred, "download_dermapred_dataset", fake_download)
    output_path = tmp_path / "raw_data"

    exit_code = download_dermapred.main([str(output_path), "--size", "128"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert calls == [(output_path, 128)]
    assert captured.out == f"Created images in directory: {output_path}\n"
    assert captured.err == ""


def test_main_reports_download_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The CLI should turn expected download errors into a failure status."""
    def fake_download(output_dir: str | Path, size: int) -> None:
        raise OSError("download failed")

    monkeypatch.setattr(download_dermapred, "download_dermapred_dataset", fake_download)

    exit_code = download_dermapred.main([str(tmp_path)])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert captured.out == ""
    assert captured.err == "Error: download failed\n"
