"""Download the DermaMNIST data used by the Dermapred example.

Run these commands from the repository root. To install the training
dependencies and download the default 64 x 64 dataset::

    uv sync --group train
    uv run --group train python -m dermapred.data.download_data data/raw_data

To select another supported image size, use ``--size``; for example::

    uv run --group train python -m dermapred.data.download_data data/raw_data --size 128

The script creates separate image and label arrays for the training,
validation, and test splits. It replaces files with the same names in the
output directory.

After inspecting the arrays, add them individually to DVC, stage their
metadata in Git, and upload the data to the configured DVC remote::

    uv run dvc add data/raw_data/*.npy
    git add data/raw_data/*.dvc data/raw_data/.gitignore data/raw_data/dataset.yaml
    uv run dvc push
    git commit -m "Track DermaMNIST data"

``dvc add`` stores each array in the local cache and creates a corresponding
``.npy.dvc`` file. Tracking the arrays separately allows DVC to transfer only
the files that change instead of treating the complete directory as one
dataset. ``dvc push`` uploads content not already present in the remote.
Commit the ``.dvc`` files so Git records which data versions belong with the
code. A DVC remote must be configured before running ``dvc push``.

Note:
    ``dataset.yaml`` is written beside the arrays as a human-readable record
    of their source, size, and MedMNIST dependency version. It is deliberately
    excluded from the ``dvc add`` command and tracked directly by Git. Commit
    it together with the generated ``.dvc`` files so their provenance remains
    aligned.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from importlib.metadata import version as package_version
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

        # Keep Git-tracked provenance beside the individually DVC-tracked arrays.
        metadata = (
            "name: DermaMNIST\n"
            f"image_size: {size}\n"
            f'medmnist_version: "{package_version("medmnist")}"\n'
            "source: https://medmnist.com/\n"
        )
        (output_path / "dataset.yaml").write_text(metadata, encoding="utf-8")


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
