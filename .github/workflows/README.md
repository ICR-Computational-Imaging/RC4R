# GitHub workflows

GitHub Actions workflows automate tasks that should run consistently whenever
something happens in a repository. For example, a workflow can check the code
after a change is pushed, run the test suite for a pull request, publish the
documentation, or create a release.

GitHub discovers workflow definitions from YAML files stored in this directory.
Each workflow specifies:

- **Events** that trigger it, such as a push, pull request, version tag, or
  manual request.
- **Jobs** that should run in response to the event.
- **Runners**, which are the temporary computers used to execute those jobs.
- **Steps**, which run commands or reusable GitHub Actions on a runner.

A typical workflow follows this sequence:

```text
Repository event -> workflow -> job -> steps -> result
```

The result and logs for each run are available from the repository's
**Actions** tab. A successful result confirms that every required step
completed; a failed result provides logs showing which step needs attention.

Only files ending in `.yml` or `.yaml` are interpreted as workflows. This
`README.md` file provides documentation and is not executed by GitHub.

## Workflows in this repository

The sections below describe the purpose, triggers, and requirements of each
workflow included in this repository.

### Unit tests (`tests.yaml`)

Runs the full pytest suite on Ubuntu with Python 3.11 and 3.12 for pushes to
*any branch*, pull requests, and manual requests. It installs the locked
`pytest` and `train` dependency groups; training imports require the latter
even for unit tests.
Tests use synthetic data and mocked transfers, so no private data, DVC remotes,
or release credentials are needed. Pytest's configured coverage report appears
in the job log.

After pushing the workflow, inspect the **Actions** tab or the PR checks. The
jobs are named `Pytest (Python 3.11)` and `Pytest (Python 3.12)`. An admin can
require both checks in the rules for `main`; adding the workflow alone does not
make them mandatory. Fork PRs may require a maintainer to approve the run.

Run the same checks locally with:

```bash
uv run --locked --no-default-groups --group pytest --group train pytest
```
