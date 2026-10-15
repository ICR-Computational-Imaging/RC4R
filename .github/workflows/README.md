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
`pytest` and `train` dependency groups and the optional `ui` extra; training
imports require the training group even for unit tests. Qt uses its offscreen
platform, and a separate check enforces at least 80% coverage of `dermapred.ui`.
Tests use synthetic data and mocked transfers, so no private data, DVC remotes,
or release credentials are needed. Pytest's configured coverage report appears
in the job log.

After pushing the workflow, inspect the **Actions** tab or the PR checks. The
jobs are named `Pytest (Python 3.11)` and `Pytest (Python 3.12)`. An admin can
require both checks in the rules for `main`; adding the workflow alone does not
make them mandatory. Fork PRs may require a maintainer to approve the run.

Run the same checks locally with:

```bash
QT_QPA_PLATFORM=offscreen uv run --locked --no-default-groups --group pytest --group train --extra ui pytest
```

### Package publishing (`publish.yaml`)

Runs manually against a version tag and publishes to the selected registry,
`testpypi` by default or `pypi` when selected explicitly. It verifies the tag
matches `VERSION`, runs synthetic tests, builds the wheel and source archive,
and imports the installed wheel outside the checkout. GitHub shows the source
tag and commit on the run; the run name shows the target registry. The built
distributions are saved as the `python-distributions` artifact, then retrieved
by the publication job. This keeps package building and uploading as separate,
visible steps.

The publication job uses an API token from the matching GitHub environment.
Configure `testpypi` and `pypi` environments, each with an environment secret
named `PYPI_API_TOKEN`. Store a TestPyPI token in `testpypi` and a PyPI token in
`pypi`. Configure required reviewers on GitHub if publication
should require approval; the workflow alone does not enforce that review.
The token is passed to uv only in the upload step. Trusted Publishing is
disabled and the job has no `id-token: write` permission. A missing secret
causes a clear error before upload.

Create and push the release tag yourself. The workflow does not change versions,
create tags, commit, or run the DVC pipelines. Pushing a tag alone does not
publish the package. After the workflow has been merged into the default branch,
start a run explicitly:

```bash
gh workflow run publish.yaml --ref v0.1.0 -f registry=testpypi
```

After checking the TestPyPI installation, publish the same reviewed tag:

```bash
gh workflow run publish.yaml --ref v0.1.0 -f registry=pypi
```

See the [publishing walkthrough](../../docs/general/publishing_to_pypi.md)
for account setup, API-token creation, GitHub secrets, tagging prerequisites,
and checks.
