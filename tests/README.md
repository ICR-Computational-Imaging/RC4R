# Project tests

This directory contains the automated tests for Dermapred. Tests check that
the code behaves as expected and help detect unintended changes before they
are merged or released.

The project uses [pytest](https://docs.pytest.org/) to discover and run tests.
Pytest finds files named `test_*.py` or `*_test.py` and runs functions whose
names begin with `test_`.

Where practical, the test structure should reflect the package structure:

```text
src/dermapred/inference/       -> tests/inference/
src/dermapred/training/        -> tests/training/
src/dermapred/evaluation/      -> tests/evaluation/
```

Tests should be small, deterministic, and independent. A test should prepare
its inputs, exercise one behaviour, and verify the result without depending on
the order in which other tests run.

The ordinary test suite must not require network access, a configured DVC
remote, or the complete DermaMNIST dataset. Use small synthetic arrays or
committed, non-sensitive fixtures where representative data are needed. Full
pipeline and model-quality checks can be kept separate from fast unit tests.

The default development environment includes the `test` dependency group.
Synchronise it and run the complete suite from the repository root:

```bash
uv sync
uv run pytest
```

The pytest configuration in `pyproject.toml` enables coverage reporting for
the `dermapred` package. To run one file or one test while developing, pass its
path or node identifier:

```bash
uv run pytest tests/inference/test_predictor.py
uv run pytest tests/inference/test_predictor.py::test_predicts_one_image
```

## Running tests in GitHub Actions

The same test suite can run automatically in GitHub Actions when code is pushed
or a pull request is opened. The continuous integration workflow should create
a clean environment from the committed `uv.lock` file and then execute:

```bash
uv sync --locked
uv run pytest
```

Running the local and automated tests through the same commands helps ensure
that a result does not depend on packages or configuration available only on a
developer's computer. The workflow can use a Python version matrix to check
each version supported by the project, currently Python 3.11 and 3.12.

A failed test causes the GitHub Actions job to fail, making the result visible
on the commit or pull request. The ordinary CI test job should remain
independent of network access, DVC credentials, and the complete DermaMNIST
dataset. Full data-pipeline reproduction should use a separate workflow with
the required access controls.

The workflow definition belongs in `.github/workflows/ci.yml`. Before enabling
locked CI installation, generate and commit the lockfile:

```bash
uv lock
git add pyproject.toml uv.lock
```

Tests should cover both expected behaviour and important failure conditions.
When fixing a defect, first add a test that demonstrates the problem, then
confirm that the implementation change makes that test pass.

## Tests in this repository

### Synthetic final-evaluation pipeline check

Run the test pipeline integration check from the repository root:

```bash
uv run --group pytest --group train pytest tests/dvcstages/test_test_pipeline.py -v
```

This test copies `pipelines/test/dvc.yaml` and its source dependencies into a
temporary project, then generates 20 synthetic RGB images, binary labels, a
temporary model checkpoint, a calibration mapping, and evaluation parameters.
It runs `dvc repro` on the copied pipeline and checks processed images,
predictions, metrics, figures, and the generated lockfile.

Both preprocessing and evaluation execute their actual pipeline commands.
They reuse the installed Python environment with uv syncing disabled and
offline mode enabled. The temporary DVC repository has its own local cache
and a temporary `rds-test` remote; no pull or push is performed. Real datasets,
model outputs, pipeline lockfiles, and institutional remotes are untouched.
Pytest removes the temporary files through its normal temporary-directory
retention policy. This checks pipeline operation, not model quality.

The sections below describe the purpose, scope, fixtures, and any special
requirements of each test area in this project.
