"""DVC stage that prepares DermaMNIST images for PyTorch models."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

import numpy as np

from dermapred.data.preprocessing import preprocess_images

IMAGE_SPLITS = ("train", "validation", "test")


class PreprocessingStage:
    """Load, preprocess, and save each DermaMNIST image split."""

    def __init__(
        self,
        input_dir: Path,
        output_dir: Path,
        splits: Sequence[str] = IMAGE_SPLITS,
    ) -> None:
        """Configure the input and output directories for the stage.

        Args:
            input_dir: Directory containing the raw image arrays.
            output_dir: Directory in which processed image arrays will be
                written.
            splits: Dataset splits to process. Defaults to all valid splits.

        Returns:
            None.

        Raises:
            TypeError: If either directory is not provided as a ``Path``.
            ValueError: If splits are empty, repeated, or invalid.
        """
        if not isinstance(input_dir, Path) or not isinstance(output_dir, Path):
            raise TypeError("input_dir and output_dir must be pathlib.Path objects.")
        selected_splits = tuple(splits)
        if not selected_splits or any(split not in IMAGE_SPLITS for split in selected_splits):
            raise ValueError(f"splits must contain names from {IMAGE_SPLITS}.")
        if len(set(selected_splits)) != len(selected_splits):
            raise ValueError("splits must not contain repeated names.")

        self.input_dir = input_dir
        self.output_dir = output_dir
        self.splits = selected_splits

    def run(self) -> None:
        """Create model-ready image arrays for the selected dataset splits.

        Returns:
            None.

        Raises:
            OSError: If an input cannot be read or an output cannot be written.
            TypeError: If an input image array has a non-numeric data type.
            ValueError: If an input file is not a valid NumPy array or its
                image shape or pixel values are invalid.
        """
        self.output_dir.mkdir(parents=True, exist_ok=True)

        for split in self.splits:
            input_path = self.input_dir / f"{split}_images.npy"
            output_path = self.output_dir / f"{split}_images.npy"
            images = np.load(input_path, allow_pickle=False)
            np.save(output_path, preprocess_images(images), allow_pickle=False)


def _parse_args(arguments: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments for the preprocessing stage.

    Args:
        arguments: Optional command-line arguments. When omitted, arguments
            are read from ``sys.argv``.

    Returns:
        The validated input and output directory arguments.

    Raises:
        SystemExit: If required arguments are missing or invalid.
    """
    parser = argparse.ArgumentParser(
        description="Preprocess DermaMNIST image arrays for PyTorch models."
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        required=True,
        help="directory containing the raw image arrays",
    )
    parser.add_argument(
        "--splits",
        nargs="+",
        choices=IMAGE_SPLITS,
        default=IMAGE_SPLITS,
        help="dataset splits to process (default: train validation test)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="directory in which to save the processed image arrays",
    )
    return parser.parse_args(arguments)


if __name__ == "__main__":
    arguments = _parse_args()
    stage = PreprocessingStage(arguments.input_dir, arguments.output_dir, arguments.splits)
    stage.run()
