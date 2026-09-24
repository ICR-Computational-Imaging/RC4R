# Project scripts

This directory contains small command-line programs that support development,
maintenance, or one-time project operations. Examples include obtaining a
public demonstration dataset, checking an artifact, or preparing files for a
release.

Scripts should act as thin entry points around reusable functions from
`src/dermapred/`. Substantial data processing, model training, evaluation, and
inference logic belongs in the installable package, where it can be imported,
tested, and reused consistently.

A typical script follows this pattern:

```text
Parse command-line arguments -> call tested package code -> report the result
```

Unless a script states otherwise, run it from the repository root using the
project environment:

```bash
uv run python scripts/<script_name>.py
```

Scripts should:

- Explain their purpose, required inputs, and generated outputs.
- Accept paths and configuration as arguments rather than embedding values
  specific to one computer.
- Fail with a clear message when prerequisites are missing.
- Avoid overwriting existing data or artifacts without explicit intent.
- Never contain credentials, access tokens, or sensitive research data.

A script may bootstrap data before DVC begins managing it. Reproducible data
transformations and training steps should normally be declared in `dvc.yaml`,
even when a DVC stage invokes code through a script or Python module.

Files in this directory are not automatically installed as commands with the
Dermapred package. Commands intended for package users should instead be
declared as entry points in `pyproject.toml`.

## Scripts in this repository

The sections below describe the purpose, arguments, outputs, and usage of each
script included in this project.

### Download DermaMNIST data (`download_dermamnist.py`)

This script downloads the official training, validation, and test splits from
the 64 × 64 version of DermaMNIST. It extracts the images and labels directly
into six files:

```text
data/train_images.npy
data/train_labels.npy
data/validation_images.npy
data/validation_labels.npy
data/test_images.npy
data/test_labels.npy
```

The project does not retain a duplicate source archive. This is a one-time
bootstrap step that represents acquiring the data at the start of a research
project; it is not part of the reproducible DVC pipeline.

The `medmnist` package should be declared in the `train` dependency group in
`pyproject.toml`. After synchronising that environment, run the script from the
repository root:

```bash
uv sync --group train
uv run python scripts/download_dermamnist.py
```

After checking the six downloaded files, place them under DVC control and
upload them to the configured DVC remote:

```bash
uv run dvc add \
    data/train_images.npy data/train_labels.npy \
    data/validation_images.npy data/validation_labels.npy \
    data/test_images.npy data/test_labels.npy
git add data/*.dvc data/.gitignore
uv run dvc push
```

Commit the generated `.dvc` files and `.gitignore` update to Git. The arrays
themselves must remain outside Git and must only be stored in locations
permitted by the dataset licence and the project's data-governance
requirements.

**Prerequisite:** DVC must be [set up](404.html) in the repository before
running `dvc add`, and a DVC remote must be configured before running
`dvc push`.
