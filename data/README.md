# Project data

This directory contains the datasets used to develop, validate, and test the
project's models or algorithms. Keeping data at the repository root separates
data artifacts from the Python source code in `src/`.

Dataset files **should not be committed directly to Git**. They may be too
large for a Git repository, change independently from the source code, or
contain sensitive information that must not be published on GitHub. Instead,
this project uses Data Version Control (DVC) to record which version of a
dataset belongs to each version of the code.

When data are tracked with DVC:

- The dataset remains in the local workspace and configured DVC storage.
- DVC records the dataset's identity and version in small metadata files.
- The DVC metadata is committed to Git alongside the source code.
- An authorised contributor can retrieve the corresponding data with
  `dvc pull`.

DVC does not provide permission to use or share a dataset. Contributors must
still follow the applicable consent, licence, information-governance, and
security requirements. Sensitive or identifiable research data must never be
uploaded to a public remote or committed to Git.

## Data in this repository

The Dermapred example uses the official training, validation, and test splits
from DermaMNIST. The selected image size is defined in the repository-level
`params.yaml` under `data.dermamnist.image_size`.
Each image array and its corresponding label array are stored separately:

| File | Contents |
| --- | --- |
| `raw_data/dataset.yaml` | Dataset source, image size, and MedMNIST package version |
| `raw_data/train_images.npy` | Images used to fit the model |
| `raw_data/train_labels.npy` | Binary benign/concerning labels for the training images |
| `raw_data/validation_images.npy` | Images used to select and tune the model |
| `raw_data/validation_labels.npy` | Binary benign/concerning labels for the validation images |
| `raw_data/test_images.npy` | Images reserved for final evaluation |
| `raw_data/test_labels.npy` | Binary benign/concerning labels for the test images |

The project deliberately does not retain an additional raw archive or create
raw, intermediate, and processed subdirectories. The downloader writes the
six image and binary-label arrays plus `dataset.yaml` directly into this
directory, providing one
clear copy of the example dataset with its acquisition metadata. The array
files must remain aligned: element `n` in an image array must correspond to
element `n` in its label array.

For the binary task, label `0` means benign and label `1` means clinically
concerning. The original seven-class labels are converted during download and
are not stored separately in this example; `dataset.yaml` records this choice.

The `.npy` arrays are managed individually by DVC and excluded from Git.
`dataset.yaml`, this README, and the generated `.dvc` metadata files remain
under Git control.
