# Project data

This directory contains the datasets used to develop, validate, and test the
project's models or algorithms. Keeping data at the repository root separates
data artifacts from the Python source code in `src/`.

Dataset files **should not be committed directly to Git**. They may be too
large for a Git repository, change independently from the source code, or
contain sensitive information that must not be published on GitHub. Instead, this project
uses Data Version Control (DVC) to record which version of a dataset belongs to
each version of the code.

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

A common data lifecycle separates immutable inputs from generated outputs:

```text
raw data -> intermediate data -> processed data -> training and evaluation
```

## Data in this repository

The sections below describe the purpose, origin, access requirements, and DVC
management of each dataset or data directory used by this project.
