"""Tests for the DVC preprocessing stage."""

from pathlib import Path

import numpy as np
import pytest

from dermapred.dvcstages.preprocessing import IMAGE_SPLITS, PreprocessingStage


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
