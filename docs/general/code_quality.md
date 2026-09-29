# Code quality

## Purpose

Code-quality tools apply consistent, repeatable checks before human review.
This template uses:

- [Ruff](https://docs.astral.sh/ruff/) for Python formatting and linting.
- [mypy](https://mypy.readthedocs.io/) for static type checking.
- [pytest](https://docs.pytest.org/) for behavioural testing.
- MkDocs strict builds for documentation validation.

These tools address different questions:

| Check | Question answered |
| --- | --- |
| Formatting | Is the code presented consistently? |
| Linting | Does the code contain selected errors or maintainability problems? |
| Static typing | Are annotated values used consistently? |
| Testing | Does the code behave as the tests require? |
| Documentation build | Can the documentation be generated without warnings? |

Passing every check does not establish scientific validity or prove that the
software is correct. It provides a consistent minimum standard for changes.

## Quality standards

Code should be:

- Clear enough to review without reconstructing the author's intent.
- Explicit about inputs, outputs, errors, and important assumptions.
- Formatted consistently using the repository's tools.
- Covered by meaningful tests where behaviour could regress.
- Typed where annotations improve understanding and checking.
- Free from unexplained lint and type-checking suppressions.
- Documented at the level required by its users and maintainers.

Repository configuration is the shared standard. Do not rely on personal
editor settings that produce different results for other contributors.

## Install the development environment

Install the configured tools from the repository root:

```bash
uv sync
```

Run them through uv so every contributor uses the versions resolved in
`uv.lock`.

## Format Python with Ruff

Check formatting without changing files:

```bash
uv run ruff format --check .
```

Apply formatting with:

```bash
uv run ruff format .
```

Review `git diff` after formatting. Avoid mixing a large formatting-only change
with unrelated behavioural changes, because this makes review unnecessarily
difficult.

The formatter does not sort imports. Ruff's import rules can apply import
sorting before formatting:

```bash
uv run ruff check --select I --fix .
uv run ruff format .
```

See the [Ruff formatter guide](https://docs.astral.sh/ruff/formatter/).

## Lint Python with Ruff

Run the configured lint rules with:

```bash
uv run ruff check .
```

Apply safe automatic fixes with:

```bash
uv run ruff check --fix .
```

Always review automatic changes. Not every reported issue can or should be
fixed mechanically.

Lint configuration belongs in `pyproject.toml`, providing one version-controlled
standard for local development and continuous integration. Rule selections
should be changed deliberately and documented when their purpose is not clear.

Do not add broad ignores merely to obtain a passing result. When a suppression
is justified, make it as narrow as possible and include the rule code:

```python
import optional_backend  # noqa: F401 - imported to register the backend
```

See the [Ruff linter guide](https://docs.astral.sh/ruff/linter/) and
[configuration reference](https://docs.astral.sh/ruff/configuration/).

## Check types with mypy

Run static type checking with:

```bash
uv run mypy
```

Type annotations should clarify interfaces and allow useful checking:

```python
from pathlib import Path


def load_names(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8").splitlines()
```

Avoid using `Any` simply to silence the checker. Types also cannot express
every runtime requirement, such as array dimensions, numerical ranges, file
contents, or compatibility between saved models and software versions. Validate
these conditions explicitly where necessary.

When an external dependency lacks type information, first check for a typed
release or supported stub package. If an ignore remains necessary, restrict it
to the affected line and error code:

```python
import untyped_library  # type: ignore[import-untyped]
```

Type annotations are not normally enforced by Python at runtime. They support
readers, editors, and static analysis; they do not replace input validation or
tests.

## Test behaviour

Run the complete test suite with:

```bash
uv run pytest
```

Tests should check meaningful behaviour, boundary conditions, failures, and
important scientific invariants. Coverage is useful for locating gaps, but a
line being executed does not prove that it was tested adequately.

See [Testing with pytest](testing.md) for the project-wide testing standards.

## Validate documentation

Build the documentation with warnings treated as errors:

```bash
uv run mkdocs build --strict
```

This detects many missing pages, invalid links, plugin problems, and
configuration errors. It cannot judge whether an explanation is correct or
clear, so rendered documentation still requires review.

## Generated and exploratory files

Apply quality tools to maintained source files. Generated code, environments,
build output, downloaded third-party files, and DVC cache contents should not be
edited merely to satisfy a checker.

Notebooks can contain hidden state, saved output, and execution-order
dependencies. If notebooks form part of a reproducible result, clear or control
their outputs, document their environment, and ensure their execution order is
unambiguous. Exploratory convenience is not a substitute for maintained source
code when logic becomes part of the research pipeline.

## Recommended local sequence

Before committing a code change, apply automatic fixes and formatting:

```bash
uv run ruff check --fix .
uv run ruff format .
```

Then run the non-modifying checks:

```bash
uv run ruff format --check .
uv run ruff check .
uv run mypy
uv run pytest
uv run mkdocs build --strict
```

Finally, inspect the proposed change:

```bash
git status
git diff
```

Stage only the intended files. Generated site output, tool caches, environments,
datasets, credentials, and unrelated local changes must not enter the commit.

## Responding to a failure

When a check fails:

1. Read the complete message, path, line number, and rule or error code.
2. Determine whether the implementation, test, annotation, or configuration is
   incorrect.
3. Fix the underlying problem where possible.
4. Use a narrow suppression only when the valid behaviour cannot be represented
   accurately by the tool.
5. Explain non-obvious exceptions.
6. Run the complete check again.

Do not weaken a repository-wide standard merely because one change is
difficult to check. Configuration changes affect future work and require the
same review as source changes.

## Continuous integration

Automated checks should use the committed lockfile and the same commands used
locally:

```bash
uv sync --locked
uv run --locked ruff format --check .
uv run --locked ruff check .
uv run --locked mypy
uv run --locked pytest
uv run --locked mkdocs build --strict
```

Caching may improve speed, but the result must not depend on a warm cache or
undeclared runner state.

## Further reading

- [Ruff documentation](https://docs.astral.sh/ruff/)
- [Ruff formatter](https://docs.astral.sh/ruff/formatter/)
- [Ruff linter](https://docs.astral.sh/ruff/linter/)
- [Ruff rule reference](https://docs.astral.sh/ruff/rules/)
- [mypy documentation](https://mypy.readthedocs.io/en/stable/)
- [Python typing documentation](https://docs.python.org/3/library/typing.html)
