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
from the 64 × 64 version of DermaMNIST. Each image array and its corresponding
label array are stored separately:

| File | Contents |
| --- | --- |
| `train_images.npy` | Images used to fit the model |
| `train_labels.npy` | Labels corresponding to the training images |
| `validation_images.npy` | Images used to select and tune the model |
| `validation_labels.npy` | Labels corresponding to the validation images |
| `test_images.npy` | Images reserved for final evaluation |
| `test_labels.npy` | Labels corresponding to the test images |

The project deliberately does not retain an additional raw archive or create
raw, intermediate, and processed subdirectories. The download script writes
these six arrays directly into this directory, providing one clear copy of the
example dataset. The files must remain aligned: element `n` in an image array
must correspond to element `n` in its label array.

All six `.npy` files are managed by DVC and excluded from Git. This README and
the generated DVC metadata files remain under Git control.
