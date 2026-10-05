"""Tests for the DermaMNIST download utility."""

from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from dermapred.data import download_data


def test_create_binary_labels_uses_dermamnist_diagnoses() -> None:
    """The binary target should use the documented clinical grouping."""
    source_labels = np.arange(7, dtype=np.uint8).reshape(-1, 1)

    binary_labels = download_data.create_binary_labels(source_labels)

    np.testing.assert_array_equal(
        binary_labels,
        np.array([[1], [1], [0], [0], [1], [0], [0]], dtype=np.uint8),
    )


def test_create_binary_labels_rejects_unknown_label() -> None:
    """Unexpected source labels should not be silently classified."""
    with pytest.raises(ValueError, match="Unknown DermaMNIST labels: 7"):
        download_data.create_binary_labels(np.array([[7]], dtype=np.uint8))


def test_load_dermamnist_size_reads_nested_parameter(tmp_path: Path) -> None:
    """The acquisition setting should be read from the requested YAML file."""
    params_path = tmp_path / "params.yaml"
    params_path.write_text("data:\n  dermamnist:\n    image_size: 28\n", encoding="utf-8")

    assert download_data.load_dermamnist_size(params_path) == 28


@pytest.mark.parametrize(
    "contents",
    ["{}\n", "data:\n  dermamnist:\n    image_size: large\n"],
)
def test_load_dermamnist_size_rejects_invalid_parameter(
    tmp_path: Path,
    contents: str,
) -> None:
    """Missing and non-integer image-size settings should produce a clear error."""
    params_path = tmp_path / "params.yaml"
    params_path.write_text(contents, encoding="utf-8")

    with pytest.raises(ValueError, match="data.dermamnist.image_size"):
        download_data.load_dermamnist_size(params_path)


def test_download_dermapred_dataset_saves_all_splits(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Save development and test splits in separate folders with provenance."""
    calls: list[tuple[str, int, bool, Path]] = []

    def fake_dermamnist(*, split: str, size: int, download: bool, root: Path) -> object:
        split_number = {"train": 1, "val": 2, "test": 3}[split]
        calls.append((split, size, download, root))
        return SimpleNamespace(
            imgs=np.full((2, size, size, 3), split_number, dtype=np.uint8),
            labels=np.full((2, 1), split_number, dtype=np.uint8),
        )

    monkeypatch.setattr(download_data, "DermaMNIST", fake_dermamnist)
    monkeypatch.setattr(download_data, "package_version", lambda package: "3.0.2")
    output_path = tmp_path / "nested" / "raw_data"

    download_data.download_dermapred_dataset(output_path, size=64)

    assert [(split, size, download) for split, size, download, _ in calls] == [
        ("train", 64, True),
        ("val", 64, False),
        ("test", 64, False),
    ]
    assert len({root for *_, root in calls}) == 1

    expected_image_values = {"train": 1, "validation": 2, "test": 3}
    expected_label_values = {"train": 1, "validation": 0, "test": 0}
    for split, expected_image_value in expected_image_values.items():
        split_path = output_path / ("test" if split == "test" else "training")
        images = np.load(split_path / f"{split}_images.npy")
        labels = np.load(split_path / f"{split}_labels.npy")
        assert images.shape == (2, 64, 64, 3)
        assert labels.shape == (2, 1)
        assert labels.dtype == np.uint8
        assert np.all(images == expected_image_value)
        assert np.all(labels == expected_label_values[split])

    expected_metadata = (
        "name: DermaMNIST\n"
        "image_size: 64\n"
        "label_task: binary\n"
        "label_0: benign\n"
        "label_1: clinically_concerning\n"
        'medmnist_version: "3.0.2"\n'
        "source: https://medmnist.com/\n"
    )
    for folder, splits in [("training", ("train", "validation")), ("test", ("test",))]:
        folder_path = output_path / folder
        assert {path.name for path in folder_path.iterdir()} == {
            "dataset.yaml",
            *(f"{split}_{kind}.npy" for split in splits for kind in ("images", "labels")),
        }
        assert (folder_path / "dataset.yaml").read_text(encoding="utf-8") == expected_metadata
    assert {path.name for path in output_path.iterdir()} == {"training", "test"}


@pytest.mark.parametrize("size", [0, 32, 256])
def test_download_dermapred_dataset_rejects_unsupported_size(
    tmp_path: Path,
    size: int,
) -> None:
    """Unsupported image dimensions should fail before creating output."""
    output_path = tmp_path / "raw_data"

    with pytest.raises(ValueError, match=f"Invalid size: {size}"):
        download_data.download_dermapred_dataset(output_path, size=size)

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

    monkeypatch.setattr(download_data, "download_dermapred_dataset", fake_download)
    output_path = tmp_path / "raw_data"

    exit_code = download_data.main([str(output_path), "--size", "128"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert calls == [(output_path, 128)]
    assert captured.out == f"Created images in directory: {output_path}\n"
    assert captured.err == ""


def test_main_uses_size_from_params(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The CLI should use params.yaml when no explicit size is supplied."""
    calls: list[tuple[Path, int]] = []

    def fake_download(output_dir: str | Path, size: int) -> None:
        calls.append((Path(output_dir), size))

    params_path = tmp_path / "params.yaml"
    params_path.write_text("data:\n  dermamnist:\n    image_size: 28\n", encoding="utf-8")
    output_path = tmp_path / "raw_data"
    monkeypatch.setattr(download_data, "download_dermapred_dataset", fake_download)

    exit_code = download_data.main([str(output_path), "--params", str(params_path)])

    assert exit_code == 0
    assert calls == [(output_path, 28)]


def test_main_reports_download_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The CLI should turn expected download errors into a failure status."""

    def fake_download(output_dir: str | Path, size: int) -> None:
        raise OSError("download failed")

    monkeypatch.setattr(download_data, "download_dermapred_dataset", fake_download)

    exit_code = download_data.main([str(tmp_path), "--size", "64"])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert captured.out == ""
    assert captured.err == "Error: download failed\n"
