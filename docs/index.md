# RC4R

**A template for reproducible code in research.**

RC4R demonstrates how source code, dependencies, data, model artifacts,
testing, documentation, and automated workflows can be managed as one
reproducible Python project.

The repository is intended both as a starting point for new research projects
and as a practical example of the tools and conventions that support
reproducible computational work.

## The Dermapred example

![DermaPred](assets/logo/dermapred-logo.svg)

Dermapred is the worked example included with RC4R. It uses PyTorch to classify
skin-lesion images from the 64 × 64 version of the DermaMNIST dataset.

The completed example will demonstrate the following workflow:

```text
Acquire data
    ↓
Version data with DVC
    ↓
Train the model
    ↓
Evaluate performance
    ↓
Version the model artifact
    ↓
Run inference through the Python package or browser interface
```

!!! warning "Research use only"
    Dermapred is an educational research example. It is not a medical device
    and must not be used to make clinical decisions.

## What this project demonstrates

- Reproducible Python environments and dependency locking with `uv`
- Installable Python code using a `src` layout
- Dataset and model-artifact versioning with DVC
- PyTorch model training, evaluation, and inference
- Automated testing and coverage reporting with pytest
- Code-quality checks with Ruff and mypy
- Project and API documentation with MkDocs
- Continuous integration and deployment with GitHub Actions
- Development and release version management with bumpversion

## Quick start

Clone the repository and create the development environment:

```bash
git clone https://github.com/ICR-Computational-Imaging/RC4R.git
cd RC4R
uv sync
```

Serve the documentation locally while editing it:

```bash
uv run mkdocs serve
```

MkDocs will display the local documentation address in the terminal. Changes
to files in `docs/` are rebuilt automatically while the server is running.

Run the automated test suite with:

```bash
uv run pytest
```

Data acquisition, DVC, training, inference, and browser-interface commands will
be added as those parts of the example are implemented.

## Project organization

The main repository directories have distinct responsibilities:

| Directory | Purpose |
| --- | --- |
| `data/` | DVC-managed training, validation, and test data |
| `docs/` | Source files for this documentation website |
| `notebooks/` | Exploratory analyses and explanatory notebooks |
| `scripts/` | Small command-line and project-bootstrap utilities |
| `src/dermapred/` | Installable training, evaluation, and inference code |
| `tests/` | Automated pytest test suite |
| `.github/workflows/` | Automated testing, documentation, and release workflows |

## Reproducibility

The project combines several complementary records:

- Git records changes to source code, configuration, and DVC metadata.
- `pyproject.toml` declares project requirements and tool configuration.
- `uv.lock` records the exact resolved Python environment.
- DVC records the datasets and model artifacts associated with the code.
- Tests and GitHub Actions verify that expected behaviour can be reproduced.

Together, these records make it possible to identify and reconstruct the code,
environment, data, and model associated with a research result.

## Documentation roadmap

Detailed guides will be added for:

- Installing and adapting the template
- Understanding the repository structure
- Acquiring and versioning data
- Reproducing the training pipeline
- Evaluating and comparing models
- Installing and using the Dermapred package
- Running the browser-based interface
- Contributing changes and creating releases

## Licence and attribution

RC4R is distributed under the Apache License 2.0. Dataset-specific licensing,
attribution, and citation requirements will be documented alongside the
Dermapred data-acquisition instructions.
