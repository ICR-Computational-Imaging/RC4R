# Testing with pytest

## Purpose

Automated tests check that software behaves as expected and help detect
unintended changes. In research software, tests support reproducibility by
making important implementation assumptions explicit and repeatable.

Tests cannot establish that a scientific method is valid. They can check that
the method has been implemented as specified, handles expected inputs, and
continues to behave consistently as the code changes.

This template uses [pytest](https://docs.pytest.org/) as its test framework.

## Testing standards

Tests should be:

- **Focused**: each test should verify one clear behaviour.
- **Readable**: names and assertions should explain what is expected.
- **Independent**: tests must not depend on execution order or another test's
  state.
- **Deterministic**: repeated runs under the same conditions should give the
  same result.
- **Fast by default**: the ordinary suite should provide prompt feedback.
- **Portable**: routine tests should not depend on one contributor's computer.
- **Safe**: tests must not expose sensitive data or modify production systems.

Tests should normally avoid network access, external services, large research
datasets, and configured DVC remotes. Use small synthetic or approved test data
where representative inputs are required.

## Install and run the tests

The dependency group is named `pytest` to distinguish software testing from
held-out model evaluation. It contains pytest and its coverage plugin. Tests
of model code also need the `train` dependencies, but use synthetic fixtures
rather than private datasets.

Install the project development environment from the repository root:

```bash
uv sync --locked --group pytest --group train
```

Run the complete test suite with:

```bash
uv run --locked --group pytest --group train pytest
```

Useful variations include:

```bash
# Run one file
uv run --group pytest --group train pytest tests/test_example.py

# Run one test
uv run --group pytest --group train pytest tests/test_example.py::test_expected_behaviour

# Run tests whose names match an expression
uv run --group pytest --group train pytest -k "expected_behaviour"

# Stop after the first failure
uv run --group pytest --group train pytest -x

# Show more detail
uv run --group pytest --group train pytest -v
```

Run commands from the repository root so pytest can find the shared project
configuration.

## Organise tests

Store tests below `tests/`. Pytest normally discovers files named `test_*.py`
or `*_test.py` and functions named `test_*`.

Where helpful, arrange test directories in a way that makes their relationship
to the source code clear. Do not reproduce the source layout mechanically when
a simpler test structure is easier to understand.

A test commonly follows three steps:

1. **Arrange** the inputs and expected result.
2. **Act** by running the behaviour being tested.
3. **Assert** that the observed result is correct.

```python title="tests/test_example.py"
def test_double_returns_twice_the_input() -> None:
    value = 3

    result = double(value)

    assert result == 6
```

Use names that describe behaviour, such as `test_rejects_empty_input`, rather
than names such as `test_function_2`.

## Test important behaviour

Tests should include an appropriate selection of:

- Expected inputs and outputs.
- Boundary values and empty inputs.
- Invalid inputs and expected exceptions.
- Previously reported defects.
- Scientifically important calculations and invariants.
- Interactions between components where integration errors are possible.

Avoid writing tests solely to execute lines. Assertions should demonstrate why
the result is acceptable.

### Expected exceptions

Use `pytest.raises` when failure is the expected behaviour:

```python
import pytest


def test_rejects_negative_size() -> None:
    with pytest.raises(ValueError, match="size must be positive"):
        create_output(size=-1)
```

Match only a stable, meaningful part of the error message.

### Floating-point values

Floating-point calculations should normally use a justified tolerance:

```python
import pytest


def test_computed_ratio() -> None:
    assert computed_ratio() == pytest.approx(0.3)
```

Choose tolerances based on the calculation and its scientific requirements,
not merely to make a failing test pass.

## Reuse setup with fixtures

Fixtures provide reusable test inputs or setup. Pytest supplies useful fixtures
such as `tmp_path` for temporary files:

```python
from pathlib import Path


def test_reads_text_file(tmp_path: Path) -> None:
    input_path = tmp_path / "input.txt"
    input_path.write_text("example", encoding="utf-8")

    assert read_text(input_path) == "example"
```

Define a custom fixture only when shared setup improves clarity. Prefer narrow,
function-scoped fixtures and avoid hidden global state. Shared fixtures may be
placed in `tests/conftest.py`.

See the [pytest fixture guide](https://docs.pytest.org/en/stable/how-to/fixtures.html)
for further examples.

## Test multiple cases

Parametrisation runs one test with several sets of inputs:

```python
import pytest


@pytest.mark.parametrize(
    ("value", "expected"),
    [(0, 0), (1, 2), (-2, -4)],
)
def test_double(value: int, expected: int) -> None:
    assert double(value) == expected
```

Use parametrisation when the cases exercise the same behaviour. Separate tests
are clearer when cases require different setup or express different rules.

## Test levels

| Level | Purpose | Normal characteristics |
| --- | --- | --- |
| Unit | Check one small behaviour | Fast and isolated |
| Integration | Check components working together | May use small local fixtures |
| End-to-end | Check a complete user workflow | Slower and more resource-intensive |

Most tests should be unit or small integration tests. Keep expensive,
hardware-specific, data-dependent, or end-to-end checks separate from the
ordinary suite and document their requirements.

## Mark specialised tests

Markers label optional categories of tests. For example:

```python
import pytest


@pytest.mark.slow
def test_complete_workflow() -> None:
    ...
```

Custom markers must be registered in the pytest configuration before use:

```toml
[tool.pytest.ini_options]
markers = [
    "slow: tests that take substantially longer than the ordinary suite",
]
```

They can then be selected or excluded:

```bash
uv run --group pytest --group train pytest -m "not slow"
```

Strict marker checking treats unknown markers as errors, helping catch
misspelled or unregistered test categories.

## Coverage

Coverage reports how much source code is executed while the tests run. It can
identify untested lines and branches, but it does not measure the quality of
the assertions or prove correctness.

A coverage report typically shows:

| Value | Meaning |
| --- | --- |
| Statements | Executable statements measured in the source |
| Missing | Statements not executed by the test suite |
| Branches | Alternative paths created by decisions such as `if` statements |
| Percentage | Proportion of the measured code that was executed |

Use coverage to locate important gaps. Do not add superficial tests purely to
reach a percentage target, and do not assume that executed code has been tested
thoroughly.

## Determinism and research software

Where relevant:

- Set and record random seeds.
- Avoid dependence on current time or test execution order.
- Use temporary directories instead of fixed local paths.
- Keep network and remote-storage tests outside the ordinary suite.
- Record justified numerical tolerances.
- Test properties such as dimensions, ranges, and invariants.
- Document unavoidable differences between platforms or hardware.

A random seed alone may not guarantee identical numerical results across every
library, device, or hardware platform.

## Regression tests

When fixing a defect:

1. Add the smallest test that demonstrates the problem.
2. Confirm that the test fails for the expected reason.
3. Correct the implementation.
4. Confirm that the new test and complete suite pass.
5. Keep the test to prevent the defect from returning unnoticed.

## Automated testing

Continuous integration should recreate the committed environment and run the
same test command used locally:

```bash
uv sync --locked --no-default-groups --group pytest --group train
uv run --locked --no-default-groups --group pytest --group train pytest
```

A test that passes locally but fails in automation may depend on undeclared
packages, local files, environment variables, operating-system behaviour, or
test order. Investigate the difference rather than repeatedly rerunning the
workflow.

## Further reading

- [pytest documentation](https://docs.pytest.org/)
- [Writing pytest tests](https://docs.pytest.org/en/stable/getting-started.html)
- [pytest fixtures](https://docs.pytest.org/en/stable/how-to/fixtures.html)
- [Parametrising tests](https://docs.pytest.org/en/stable/how-to/parametrize.html)
- [Using pytest markers](https://docs.pytest.org/en/stable/how-to/mark.html)
- [pytest-cov documentation](https://pytest-cov.readthedocs.io/)
