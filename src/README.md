# Project source code

This directory contains the installable Python source code for the project.
The repository is named RC4R, while the example package distributed and
imported by users is named `dermapred`:

```python
import dermapred
```

The project uses a `src` layout, which keeps the package separate from files at
the repository root. This helps tests and development commands use the
installed package in the same way as its eventual users, rather than importing
source files accidentally from the current working directory.

The intended package structure is:

```text
src/
└── dermapred/
    ├── __init__.py
    ├── data/          # Dataset loading and preprocessing code
    ├── training/      # Model definitions and training logic
    ├── evaluation/    # Metrics and model evaluation
    └── inference/     # Model loading and prediction API
```

Each Python subpackage should contain an `__init__.py` file. The top-level
`dermapred/__init__.py` can expose a small, stable public interface for package
users while implementation details remain in their respective modules.

Code in this directory should be reusable, testable, and independent of one
developer's machine. In particular:

- Use project configuration or function arguments instead of hard-coded local
  paths.
- Keep reusable logic here rather than duplicating it in notebooks or scripts.
- Add corresponding tests under `tests/` for important behaviour and failure
  conditions.
- Document public modules, classes, and functions with docstrings
  (incorporated directly into public documentation via MkDocs).
- Avoid network access, file writes, model loading, or other expensive work at
  module import time (i.e. `import dermapred`).

Dataset files belong in the root `data/` directory, and generated model
artifacts belong in a root-level artifact directory managed by DVC. They should
not be placed inside the Python package or included in its wheel unless there
is a deliberate packaging requirement.

After synchronising the project environment, package modules can be run or
imported through `uv`:

```bash
uv sync
uv run python -c "import dermapred"
```

## Source modules in this repository

The sections below describe the responsibilities, public interfaces, and
relationships of each Dermapred source package.
