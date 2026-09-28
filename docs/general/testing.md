# Testing with pytest

## Why test research software?

Automated tests check that code behaves as expected and help detect unintended
changes before they affect an analysis or release. Tests cannot prove that a
scientific method is valid, but they can verify that its implementation follows
specified behaviour.

Useful tests answer questions such as:

- Does a function produce the expected result for a known input?
- Are invalid inputs rejected clearly?
- Do data transformations preserve required shapes, types, or ranges?
- Do several components work together correctly?
- Does a fixed defect remain fixed after later changes?

This project uses [pytest](https://docs.pytest.org/) and pytest-cov. Their
configuration is stored in `pyproject.toml`, and tests belong below `tests/`.

## Install and run the tests

The default development environment includes the `test` dependency group:

```bash
uv sync
uv run pytest
```

Run commands from the repository root. The complete suite should be the normal
check before opening a pull request.

Useful selections include:

```bash
# One file
uv run pytest tests/test_example.py

# One test
uv run pytest tests/test_example.py::test_expected_behaviour

# Tests whose names match an expression
uv run pytest -k "prediction and not slow"

# Stop after the first failure
uv run pytest -x

# Show more detail
uv run pytest -v
```

Do not routinely add options that conceal warnings or failures. A command used
for debugging should not silently become the project's quality check.

## Current pytest configuration

The `[tool.pytest.ini_options]` section of `pyproject.toml` currently defines:

| Setting | Effect |
| --- | --- |
| `testpaths = ["tests"]` | Test discovery starts below `tests/`. |
| `--strict-config` | Invalid pytest configuration is treated as an error. |
| `--strict-markers` | Unknown or misspelled markers are treated as errors. |
| `--cov=dermapred` | Coverage is collected for the `dermapred` package. |
| `--cov-report=term-missing` | Missing covered lines are listed in the terminal. |

Coverage is configured to include branch coverage and omit fully covered files
from the report. A high percentage is useful evidence, but it does not show
that assertions are scientifically meaningful or that all important cases
were considered.

## Organise tests

Pytest normally discovers files named `test_*.py` or `*_test.py` and functions
named `test_*`. Where practical, mirror the package structure:

```text
src/dermapred/inference/predictor.py
tests/inference/test_predictor.py
```

Keep each test focused on one behaviour. A simple test follows arrange, act,
assert:

```python title="tests/test_example.py"
from dermapred import example


def test_example_doubles_value() -> None:
    # Arrange
    value = 3

    # Act
    result = example(value)

    # Assert
    assert result == 6
```

The names should describe behaviour rather than implementation details. A name
such as `test_rejects_empty_input` is more informative than `test_function_2`.

## Test expected failures

Error handling is part of the interface. Use `pytest.raises` to verify that an
invalid input produces the intended exception:

```python
import pytest


def test_rejects_negative_size() -> None:
    with pytest.raises(ValueError, match="size must be positive"):
        create_output(size=-1)
```

Check a stable, meaningful part of the message rather than matching incidental
wording.

## Reuse setup with fixtures

A fixture supplies repeatable test inputs or setup. Define a fixture with
`@pytest.fixture` and request it by name:

```python
from pathlib import Path

import pytest


@pytest.fixture
def input_file(tmp_path: Path) -> Path:
    path = tmp_path / "input.txt"
    path.write_text("example", encoding="utf-8")
    return path


def test_reads_input(input_file: Path) -> None:
    assert read_input(input_file) == "example"
```

Prefer narrow fixtures with function scope. Use pytest's `tmp_path` fixture for
temporary files so tests do not write into the repository or depend on a
developer's directory layout. Shared fixtures can be placed in
`tests/conftest.py` when several test modules genuinely need them.

## Test several cases with parametrisation

Parametrisation runs one test body with several inputs:

```python
import pytest


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (0, 0),
        (1, 2),
        (-2, -4),
    ],
)
def test_double(value: int, expected: int) -> None:
    assert double(value) == expected
```

Include ordinary, boundary, and invalid cases where they are meaningful. See
the official [pytest parametrisation guide](https://docs.pytest.org/en/stable/how-to/parametrize.html).

## Unit, integration, and pipeline tests

Different scopes find different problems:

| Scope | Purpose | Typical requirements |
| --- | --- | --- |
| Unit | Check one function or class in isolation | Fast, synthetic inputs |
| Integration | Check several project components together | Small committed fixtures |
| Pipeline | Check a complete DVC or training workflow | Controlled data, more time and resources |

The ordinary test suite should remain fast and independent of network access,
RDS, a DVC remote, GPUs, and the complete research dataset. Use small synthetic
or openly distributable fixtures. Large pipeline and model-quality checks
should be explicitly separated and run only in an approved environment.

## Deterministic tests

Tests should give the same result when repeated. To improve reliability:

- Set random seeds where randomness is part of the test.
- Avoid depending on test execution order.
- Do not share mutable state between tests.
- Avoid current time, network services, and undeclared local files.
- Use tolerances such as `pytest.approx` for floating-point comparisons.
- Check properties such as shape, range, and invariants as well as exact values.

A random seed does not guarantee identical numerical results across every
library, device, or hardware platform. Document tolerances and hardware-specific
behaviour where these affect the research result.

## Mark specialised tests

Markers can identify tests that are slow or require special resources:

```python
@pytest.mark.slow
def test_complete_pipeline() -> None:
    ...
```

Because strict markers are enabled, register every custom marker in
`pyproject.toml` before using it:

```toml
[tool.pytest.ini_options]
markers = [
    "slow: tests that take substantially longer than the ordinary suite",
]
```

Then exclude it from a normal local run with:

```bash
uv run pytest -m "not slow"
```

Do not use markers to make important failing tests disappear permanently.

## Tests in pull requests

GitHub Actions should reproduce the same locked environment and command used
locally:

```bash
uv sync --locked
uv run --locked pytest
```

When a test fails in continuous integration but passes locally, compare the
Python version, operating system, installed lockfile, environment variables,
filesystem assumptions, and test order. Do not simply rerun the workflow until
an intermittent test happens to pass.

## Writing a regression test

When fixing a defect:

1. Add the smallest test that demonstrates the incorrect behaviour.
2. Confirm that it fails for the expected reason.
3. Correct the implementation.
4. Confirm that the new test and full suite pass.
5. Keep the test so later changes cannot silently reintroduce the defect.

## Further reading

- [pytest documentation](https://docs.pytest.org/)
- [How to use fixtures](https://docs.pytest.org/en/stable/how-to/fixtures.html)
- [Parametrising tests](https://docs.pytest.org/en/stable/how-to/parametrize.html)
- [Using pytest markers](https://docs.pytest.org/en/stable/how-to/mark.html)
- [pytest-cov documentation](https://pytest-cov.readthedocs.io/)

