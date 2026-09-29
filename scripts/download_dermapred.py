"""Download the DermaMNIST data used by the Dermapred example.

Run these commands from the repository root. First install the training
dependencies and download the default 64 x 64 dataset::

    uv sync --group train
    uv run python scripts/download_dermapred.py data/raw_data

To select another supported image size, add ``--size``; for example::

    uv run python scripts/download_dermapred.py data/raw_data --size 128

The script creates separate image and label arrays for the training,
validation, and test splits. It replaces files with the same names in the
output directory.

After inspecting the generated arrays, add or update them in DVC::

    uv run dvc add data/raw_data/*.npy
    git add data/raw_data/*.dvc data/raw_data/.gitignore
    uv run dvc push

``dvc add`` updates the local DVC metadata; it does not upload the arrays.
``dvc push`` uploads the tracked data to the configured DVC remote. Review and
commit the changed ``.dvc`` files and ``.gitignore`` so Git records which data
version belongs with the code. A DVC remote must be configured before running
``dvc push``.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np
from medmnist import DermaMNIST

DEFAULT_SIZE = 64
AVAILABLE_SIZES = (28, 64, 128, 224)


def download_dermapred_dataset(output_dir: str | Path, size: int = DEFAULT_SIZE) -> None:
    """Download the raw dermapred dataset from the original source.

    Args:
        output_dir: Destination directory for the raw dermapred numpy dataset.
        size: The width and height of each DermaMNIST image.
              Must be one of 28, 64, 128, or 224 (default: 64).

    Raises:
        ValueError: If the size is not one of 28, 64, 128, or 224.
        OSError: If the dataset cannot be downloaded or saved.
    """
    if size not in AVAILABLE_SIZES:
        valid_sizes = ", ".join(str(valid_size) for valid_size in AVAILABLE_SIZES)
        raise ValueError(f"Invalid size: {size}. Must be one of {valid_sizes}.")

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    with TemporaryDirectory() as temporary_directory:
        # Download dataset to temp directory.
        temp_path = Path(temporary_directory)

        data_train = DermaMNIST(split="train", size=size, download=True, root=temp_path)
        data_val = DermaMNIST(split="val", size=size, download=False, root=temp_path)
        data_test = DermaMNIST(split="test", size=size, download=False, root=temp_path)

        # Save the labels as numpy arrays in the output directory.
        np.save(output_path / "train_labels.npy", data_train.labels)
        np.save(output_path / "validation_labels.npy", data_val.labels)
        np.save(output_path / "test_labels.npy", data_test.labels)

        # Save the images as numpy arrays in the output directory.
        np.save(output_path / "train_images.npy", data_train.imgs)
        np.save(output_path / "validation_images.npy", data_val.imgs)
        np.save(output_path / "test_images.npy", data_test.imgs)


def _parse_args(arguments: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description=("Download the raw dermapred dataset from the original source.")
    )
    parser.add_argument(
        "output", type=Path, help="destination directory for raw dermapred numpy dataset"
    )
    parser.add_argument(
        "--size",
        type=int,
        default=DEFAULT_SIZE,
        choices=AVAILABLE_SIZES,
        help="image width and height (default: 64)",
    )
    return parser.parse_args(arguments)


def main(arguments: Sequence[str] | None = None) -> int:
    """Run the DermaMNIST command-line interface."""
    args = _parse_args(arguments)

    try:
        download_dermapred_dataset(args.output, args.size)
    except (OSError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1

    print(f"Created images in directory: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
