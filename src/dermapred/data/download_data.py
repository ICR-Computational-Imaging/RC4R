r"""Download the DermaMNIST data used by the Dermapred example.

This downloader is for the public, openly available DermaMNIST example data.
It downloads all splits, including test data, for anyone who runs it. Separate
output folders organize this example; they do not enforce restricted access.
Real projects should obtain restricted training and held-out test datasets
through institution-approved access controls (e.g. RDS directories with explicit 
access permissions for maintainers and contributors) instead of using this downloader.

The image size is read from ``data.dermamnist.image_size`` in ``params.yaml``.
Run these commands from the repository root to install the training
dependencies and download the configured dataset::

    uv sync --group train
    uv run --group train python -m dermapred.data.download_data data/raw_data

Change ``params.yaml`` to select another size permanently. For a temporary
override, use ``--size``::

    uv run --group train python -m dermapred.data.download_data data/raw_data --size 128

The script creates separate image and binary label arrays for the training,
validation, and test splits. For this first classification task, ``0`` means
benign and ``1`` means clinically concerning. The original seven-class labels
are converted before saving. The script replaces files with the same names in
the output directory.

Data will be stored in separate locations for training/validation and test:

    - data/raw_data/training: Contains the training and validation images and labels.
    - data/raw_data/test: Contains the test images and labels.

After inspecting the arrays, add them individually to DVC. A ``-r`` option
on ``dvc push`` selects a destination for each group separately::

Training:
    uv run dvc add data/raw_data/training/*.npy
    git add params.yaml data/raw_data/training/*.dvc data/raw_data/training/.gitignore \
        data/raw_data/training/dataset.yaml
    uv run dvc push -r rds-train data/raw_data/training/*.dvc
    git commit -m "Track DermaMNIST training data"

Test:
    uv run dvc add data/raw_data/test/*.npy
    git add params.yaml data/raw_data/test/*.dvc data/raw_data/test/.gitignore \
        data/raw_data/test/dataset.yaml
    uv run dvc push -r rds-test data/raw_data/test/*.dvc
    git commit -m "Track DermaMNIST test data"

``dvc add`` stores each array in the local cache and creates a corresponding
``.npy.dvc`` file. Tracking the arrays separately allows DVC to transfer only
the files that change instead of treating the complete directory as one
dataset. ``dvc push`` uploads content not already present in the remote.
Commit the ``.dvc`` files so Git records which data versions belong with the
code. A DVC remote must be configured before running ``dvc push``.

An optional alternative is to assign remote fields within each ``.npy.dvc`` file before
staging them in Git. Open each .npy.dvc file and add the appropriate remote field::

    outs:
    - md5: ...       # Keep the generated value
      size: ...      # Keep the generated value
      hash: md5
      path: ...      # Keep the generated value
      remote: rds-train
        
Use ``remote: rds-test`` for the test arrays.

Once the remote fields are assigned, an authorized person with access to both
remotes can use a single command to upload all tracked content to its assigned
remote (or the default remote for any unassigned outputs)::

    uv run dvc push

Dermapred deliberately keeps remote selection manual instead of recording
``remote`` fields in the generated ``.npy.dvc`` files. Contributors may have
access to training and validation data without access to the test remote.
Selecting both the dataset targets and the remote makes each transfer explicit.
A blanket ``dvc pull`` with saved test-remote assignments can fail when test
data need downloading and that remote is inaccessible. Without assignments,
a blanket pull uses the default remote and may fail because test data are not
stored there. Use targeted commands in either case.

After cloning or updating the Git repository, pull the datasets you are
authorized to access. The committed ``.dvc`` files must be present first;
there is no need to run this downloader or ``dvc add`` again::

    # Contributors: retrieve training and validation arrays only.
    uv run dvc pull -r rds-train data/raw_data/training/*.dvc

    # Authorized evaluators: retrieve test arrays only.
    uv run dvc pull -r rds-test data/raw_data/test/*.dvc

These commands retrieve the raw arrays, not processed data or model outputs.
``dataset.yaml`` comes from Git. Without saved remote assignments, always
specify ``-r rds-test`` when pulling or pushing test data; otherwise DVC uses
the default remote. Storage permissions, rather than these commands, enforce
who can access each remote.
    
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
import yaml
from medmnist import DermaMNIST
from medmnist.info import INFO

AVAILABLE_SIZES = (28, 64, 128, 224)
DEFAULT_PARAMS_PATH = Path("params.yaml")
CONCERNING_DIAGNOSES = frozenset(
    {
        "actinic keratoses and intraepithelial carcinoma",
        "basal cell carcinoma",
        "melanoma",
    }
)


def create_binary_labels(labels: np.ndarray) -> np.ndarray:
    """Map DermaMNIST labels to benign or clinically concerning classes.

    The diagnosis names are deliberately selected here, while MedMNIST's
    ``INFO`` dictionary remains the authority for their numeric labels. The
    original array shape is retained so the derived labels align directly
    with the source labels.

    Args:
        labels: Original integer DermaMNIST labels.

    Returns:
        An unsigned-byte array where 0 is benign and 1 is clinically
        concerning.

    Raises:
        ValueError: If the expected diagnoses or input labels are not present
            in the installed MedMNIST metadata.
    """
    label_metadata = INFO["dermamnist"]["label"]
    available_diagnoses = set(label_metadata.values())
    missing_diagnoses = CONCERNING_DIAGNOSES - available_diagnoses
    if missing_diagnoses:
        missing = ", ".join(sorted(missing_diagnoses))
        raise ValueError(f"Missing diagnoses in MedMNIST metadata: {missing}")

    binary_mapping = {
        int(label): int(diagnosis in CONCERNING_DIAGNOSES)
        for label, diagnosis in label_metadata.items()
    }
    unique_labels = {int(label) for label in np.unique(labels)}
    unknown_labels = unique_labels - binary_mapping.keys()
    if unknown_labels:
        unknown = ", ".join(str(label) for label in sorted(unknown_labels))
        raise ValueError(f"Unknown DermaMNIST labels: {unknown}")

    lookup = np.array(
        [binary_mapping[index] for index in range(len(binary_mapping))],
        dtype=np.uint8,
    )
    return lookup[labels]


def load_dermamnist_size(params_path: str | Path = DEFAULT_PARAMS_PATH) -> int:
    """Read the configured DermaMNIST image size from a YAML parameters file.

    Args:
        params_path: YAML file containing ``data.dermamnist.image_size``.

    Returns:
        The configured image width and height.

    Raises:
        OSError: If the parameters file cannot be read.
        ValueError: If the required integer parameter is missing or malformed.
    """
    path = Path(params_path)
    try:
        parameters = yaml.safe_load(path.read_text(encoding="utf-8"))
        size = parameters["data"]["dermamnist"]["image_size"]
    except (TypeError, KeyError, yaml.YAMLError) as error:
        raise ValueError(f"{path} must define an integer at data.dermamnist.image_size") from error

    if isinstance(size, bool) or not isinstance(size, int):
        raise ValueError(f"{path} must define an integer at data.dermamnist.image_size")

    return size


def download_dermapred_dataset(output_dir: str | Path, size: int) -> None:
    """Download the raw dermapred dataset from the original source.

    Args:
        output_dir: Destination directory for the raw dermapred numpy dataset.
        size: The width and height of each DermaMNIST image.
              Must be one of 28, 64, 128, or 224.

    Raises:
        ValueError: If the size is not one of 28, 64, 128, or 224.
        OSError: If the dataset cannot be downloaded or saved.
    """
    if size not in AVAILABLE_SIZES:
        valid_sizes = ", ".join(str(valid_size) for valid_size in AVAILABLE_SIZES)
        raise ValueError(f"Invalid size: {size}. Must be one of {valid_sizes}.")

    output_path_train = Path(output_dir) / "training"
    output_path_test = Path(output_dir) / "test"

    for path in [output_path_train, output_path_test]:
        path.mkdir(parents=True, exist_ok=True)

    with TemporaryDirectory() as temporary_directory:
        # Download dataset to temp directory.
        temp_path = Path(temporary_directory)

        data_train = DermaMNIST(split="train", size=size, download=True, root=temp_path)
        data_val = DermaMNIST(split="val", size=size, download=False, root=temp_path)
        data_test = DermaMNIST(split="test", size=size, download=False, root=temp_path)

        # Convert the seven source diagnoses into the binary modelling target.
        np.save(
            output_path_train / "train_labels.npy",
            create_binary_labels(data_train.labels),
        )
        np.save(
            output_path_train / "validation_labels.npy",
            create_binary_labels(data_val.labels),
        )
        np.save(
            output_path_test / "test_labels.npy",
            create_binary_labels(data_test.labels),
        )

        # Save the images as numpy arrays in the output directory.
        np.save(output_path_train / "train_images.npy", data_train.imgs)
        np.save(output_path_train / "validation_images.npy", data_val.imgs)
        np.save(output_path_test / "test_images.npy", data_test.imgs)

        # Keep Git-tracked provenance beside the individually DVC-tracked arrays.
        metadata = (
            "name: DermaMNIST\n"
            f"image_size: {size}\n"
            "label_task: binary\n"
            "label_0: benign\n"
            "label_1: clinically_concerning\n"
            f'medmnist_version: "{package_version("medmnist")}"\n'
            "source: https://medmnist.com/\n"
        )
        (output_path_train / "dataset.yaml").write_text(metadata, encoding="utf-8")
        (output_path_test / "dataset.yaml").write_text(metadata, encoding="utf-8")


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
        default=None,
        choices=AVAILABLE_SIZES,
        help="override the image size configured in params.yaml",
    )
    parser.add_argument(
        "--params",
        type=Path,
        default=DEFAULT_PARAMS_PATH,
        help="parameters file used when --size is omitted (default: params.yaml)",
    )
    return parser.parse_args(arguments)


def main(arguments: Sequence[str] | None = None) -> int:
    """Run the DermaMNIST command-line interface."""
    args = _parse_args(arguments)

    try:
        size = args.size if args.size is not None else load_dermamnist_size(args.params)
        download_dermapred_dataset(args.output, size)
    except (OSError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1

    print(f"Created images in directory: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
