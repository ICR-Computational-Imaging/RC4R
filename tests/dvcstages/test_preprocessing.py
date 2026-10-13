"""Tests for the DVC preprocessing stage."""

from pathlib import Path

import numpy as np
import pytest

from dermapred.dvcstages.preprocessing import IMAGE_SPLITS, PreprocessingStage, _parse_args


def test_preprocessing_stage_requires_path_objects(tmp_path: Path) -> None:
    """Stage paths should be explicit pathlib objects."""
    with pytest.raises(TypeError, match="pathlib.Path"):
        PreprocessingStage("raw_data", tmp_path)  # type: ignore[arg-type]


def test_preprocessing_stage_writes_all_image_splits(tmp_path: Path) -> None:
    """The stage should write a processed array for every source split."""
    input_dir = tmp_path / "raw_data"
    output_dir = tmp_path / "processed_data"
    input_dir.mkdir()

    for index, split in enumerate(IMAGE_SPLITS):
        images = np.full((2, 4, 5, 3), index * 127, dtype=np.uint8)
        np.save(input_dir / f"{split}_images.npy", images)

    PreprocessingStage(input_dir, output_dir).run()

    for split in IMAGE_SPLITS:
        processed = np.load(output_dir / f"{split}_images.npy")
        assert processed.shape == (2, 3, 4, 5)
        assert processed.dtype == np.float32


@pytest.mark.parametrize("splits", [("train", "validation"), ("test",)])
def test_selected_splits_do_not_require_other_data(tmp_path: Path, splits: tuple[str, ...]) -> None:
    """Separate pipelines work when only their selected data is accessible."""
    input_dir = tmp_path / "raw"
    output_dir = tmp_path / "processed"
    input_dir.mkdir()
    for split in splits:
        np.save(input_dir / f"{split}_images.npy", np.zeros((2, 4, 5, 3), dtype=np.uint8))
    PreprocessingStage(input_dir, output_dir, splits).run()
    assert {path.name for path in output_dir.iterdir()} == {
        f"{split}_images.npy" for split in splits
    }


def test_missing_selected_split_fails(tmp_path: Path) -> None:
    """Required data must not be silently skipped."""
    with pytest.raises(FileNotFoundError):
        PreprocessingStage(tmp_path, tmp_path / "processed", ("test",)).run()


@pytest.mark.parametrize("splits", [(), ("unknown",), ("../test",), ("train", "train")])
def test_invalid_splits_rejected(tmp_path: Path, splits: tuple[str, ...]) -> None:
    """Validate Python callers before creating outputs or loading arrays."""
    output_dir = tmp_path / "processed"
    with pytest.raises(ValueError, match="splits"):
        PreprocessingStage(tmp_path, output_dir, splits)
    assert not output_dir.exists()


def test_cli_selects_splits() -> None:
    """The CLI exposes the selection used by each pipeline."""
    arguments = _parse_args(
        [
            "--input-dir",
            "raw",
            "--output-dir",
            "processed",
            "--splits",
            "train",
            "validation",
        ]
    )
    assert arguments.splits == ["train", "validation"]


def test_cli_defaults_to_all_splits() -> None:
    """Existing commands continue to process all splits."""
    arguments = _parse_args(["--input-dir", "raw", "--output-dir", "processed"])
    assert tuple(arguments.splits) == IMAGE_SPLITS


@pytest.mark.parametrize("selection", [[], ["unknown"]])
def test_cli_rejects_empty_or_unknown_selection(selection: list[str]) -> None:
    """Invalid CLI selections fail at argument parsing."""
    with pytest.raises(SystemExit):
        _parse_args(["--input-dir", "raw", "--output-dir", "processed", "--splits", *selection])
