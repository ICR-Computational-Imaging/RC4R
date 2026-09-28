# Code quality

## Introduction

Code-quality tools provide quick, repeatable feedback before review. They
complement tests rather than replacing them:

| Check | Tool | Question answered |
| --- | --- | --- |
| Formatting | Ruff formatter | Is the Python code presented consistently? |
| Linting | Ruff linter | Does the code contain selected errors or maintainability problems? |
| Static typing | mypy | Are annotated values used consistently? |
| Testing | pytest | Does the code behave as the tests require? |

Passing every tool does not prove that an algorithm is correct, scientifically
valid, secure, or suitable for clinical use. It establishes a useful minimum
standard for implementation quality.

## Install the development tools

Ruff and mypy are included in the default development environment:

```bash
uv sync
```

Run the complete local quality check from the repository root:

```bash
uv run ruff format --check .
uv run ruff check .
uv run mypy
uv run pytest
uv run mkdocs build --strict
```

The order gives fast feedback first and leaves tests and documentation builds
until after basic source problems have been found.

## Format Python with Ruff

Formatting applies a consistent layout automatically. Check whether files are
already formatted without modifying them:

```bash
uv run ruff format --check .
```

Format them in place with:

```bash
uv run ruff format .
```

Review `git diff` afterward. Formatting should not be mixed with unrelated
behaviour changes in a large, difficult-to-review commit.

The formatter does not sort imports. Import sorting is supplied by Ruff's `I`
lint rules and can be applied using the lint fixer before formatting:

```bash
uv run ruff check --select I --fix .
uv run ruff format .
```

See the official [Ruff formatter guide](https://docs.astral.sh/ruff/formatter/).

## Lint Python with Ruff

Run the configured linter with:

```bash
uv run ruff check .
```

The current `pyproject.toml` configuration uses a line length of 100, targets
Python 3.11, and enables these rule groups:

| Prefix | Source | Examples of issues found |
| --- | --- | --- |
| `E` | pycodestyle errors | Invalid whitespace and other style errors |
| `F` | Pyflakes | Undefined names and unused imports |
| `I` | isort | Incorrectly ordered imports |
| `UP` | pyupgrade | Syntax that can be modernised for supported Python versions |

Many findings can be fixed automatically:

```bash
uv run ruff check --fix .
```

Always review automatic changes. Ruff intentionally leaves some potentially
unsafe fixes unapplied unless they are explicitly enabled. Do not add blanket
ignores merely to obtain a green check; understand the finding and use the
narrowest justified suppression.

For a single intentional exception, include the rule code and, where useful,
an explanation:

```python
import optional_backend  # noqa: F401 - imported to register the backend
```

Project-wide rule selection and justified per-file exceptions belong in
`pyproject.toml`, not in undocumented command-line aliases. See the
[Ruff linter guide](https://docs.astral.sh/ruff/linter/) and
[configuration reference](https://docs.astral.sh/ruff/configuration/).

## Check types with mypy

Type annotations describe what values a function expects and returns. Mypy
checks those annotations without running the program:

```bash
uv run mypy
```

The current configuration checks `src/` and `tests/`, targets Python 3.11, and
enables strict mode. New public code should therefore provide useful argument
and return annotations:

```python
from pathlib import Path


def load_names(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8").splitlines()
```

Annotations should express meaningful interfaces rather than silence the
checker with `Any`. Use explicit validation for information that types cannot
guarantee, such as array dimensions, numeric ranges, file contents, or model
compatibility.

When a third-party package lacks type information, first check whether a typed
version or stub package is available. If an ignore is necessary, restrict it to
the affected line and error code instead of disabling checking for the whole
project:

```python
import untyped_library  # type: ignore[import-untyped]
```

See the [mypy documentation](https://mypy.readthedocs.io/en/stable/) and its
[configuration reference](https://mypy.readthedocs.io/en/stable/config_file.html).

## Type hints at runtime

Python does not normally enforce annotations when a program runs. For example,
an annotation of `Path` helps readers, editors, and mypy, but does not itself
reject a string at runtime. Add explicit runtime validation when invalid input
could produce an unclear error or unsafe result.

Avoid importing heavy optional libraries solely for annotations at runtime.
Where appropriate, use `from __future__ import annotations` and
`typing.TYPE_CHECKING` while keeping the module understandable.

## Notebooks and generated files

Notebooks are useful for exploration but can contain hidden state, large
outputs, and execution-order dependencies. Ruff may discover Jupyter notebooks
by default. Review notebook findings rather than assuming that all exploratory
files meet package-source standards immediately.

Do not edit generated files merely to satisfy a style tool. Generated Python,
build output, environments, DVC cache content, and downloaded third-party code
should be excluded or regenerated from their source.

## Recommended pre-commit sequence

Before committing a source-code change:

```bash
uv run ruff check --fix .
uv run ruff format .
uv run ruff format --check .
uv run ruff check .
uv run mypy
uv run pytest
```

Then inspect the actual change:

```bash
git status
git diff
```

The first two commands may modify files; the remaining quality checks should
be read-only. A pull request should normally contain the formatted source and
pass the same non-modifying checks in GitHub Actions.

## Handling a reported problem

When a quality check fails:

1. Read the file, line number, rule or error code, and complete message.
2. Decide whether the implementation or its declared interface is wrong.
3. Fix the underlying issue when possible.
4. Add a narrow suppression only when the tool cannot represent the valid
   behaviour.
5. Explain non-obvious suppressions in a comment.
6. Run the complete check again.

Do not weaken repository-wide configuration simply because one change is
difficult to type or lint. Configuration changes affect every future file and
deserve the same review as source changes.

## Further reading

- [Ruff documentation](https://docs.astral.sh/ruff/)
- [Ruff formatter](https://docs.astral.sh/ruff/formatter/)
- [Ruff linter](https://docs.astral.sh/ruff/linter/)
- [Ruff rule reference](https://docs.astral.sh/ruff/rules/)
- [mypy documentation](https://mypy.readthedocs.io/en/stable/)
- [Python typing documentation](https://docs.python.org/3/library/typing.html)

