# Automation with GitHub Actions

## Introduction

[GitHub Actions](https://docs.github.com/en/actions) runs automated tasks in
response to repository events. A workflow can test a pull request, check code
quality, build documentation, publish GitHub Pages, or prepare a release in a
fresh, repeatable environment.

Automation provides independent evidence that a change does not rely on one
contributor's local environment. It does not replace review: a successful
workflow only confirms that its declared checks passed.

GitHub reads workflow files ending in `.yml` or `.yaml` from:

```text
.github/workflows/
```

The README in that directory is explanatory documentation and is not executed.

## Workflow concepts

The main components are:

| Component | Purpose |
| --- | --- |
| Workflow | The complete YAML automation definition. |
| Event | An occurrence that starts a workflow, such as `push`, `pull_request`, or a manual request. |
| Job | A group of steps run on one fresh runner. Jobs can depend on other jobs. |
| Runner | The temporary machine that executes a job, such as an Ubuntu runner. |
| Step | One action or shell command within a job. |
| Action | A reusable automation component referenced with `uses`. |
| Artifact | Files retained or passed between jobs, such as a built documentation site. |
| Secret | An encrypted repository or environment value made available only where authorised. |

The normal execution flow is:

```text
Repository event → workflow → jobs → steps → checks and artifacts
```

Jobs run independently unless `needs` declares an ordering dependency. Steps
inside one job run in order and share that job's checked-out workspace.

## Current documentation workflow

This repository currently contains `.github/workflows/docs.yaml`. It:

1. Runs after relevant documentation files are pushed to `main`, or when
   started manually.
2. Checks out the repository on a fresh Ubuntu runner.
3. Installs uv and Python 3.11.
4. Recreates the locked documentation environment.
5. Builds the MkDocs site in strict mode.
6. Uploads the generated site as a GitHub Pages artifact.
7. Deploys the artifact in a separate job.

Path filters avoid rebuilding the documentation after an unrelated change.
The deploy job depends on the build job, so a failed build cannot be published.
The complete publishing setup is described in
[Publishing documentation with GitHub Pages](github-pages.md).

## A basic continuous-integration workflow

The repository does not yet contain a general code-quality workflow. When the
source and tests are ready, a file such as `.github/workflows/ci.yaml` could
start with:

```yaml title=".github/workflows/ci.yaml"
name: Continuous integration

on:
  pull_request:
  push:
    branches:
      - main
      - dev
  workflow_dispatch:

permissions:
  contents: read

jobs:
  quality:
    name: Test and check code
    runs-on: ubuntu-latest

    steps:
      - name: Check out repository
        uses: actions/checkout@v7

      - name: Install uv
        uses: astral-sh/setup-uv@v10
        with:
          enable-cache: true

      - name: Install Python
        run: uv python install 3.11

      - name: Install locked development environment
        run: uv sync --locked

      - name: Check formatting
        run: uv run --locked ruff format --check .

      - name: Lint
        run: uv run --locked ruff check .

      - name: Check types
        run: uv run --locked mypy

      - name: Run tests
        run: uv run --locked pytest
```

This is an example for a future workflow, not a description of a currently
active `ci.yaml`. Review action versions and project requirements when the file
is introduced.

Using `--locked` prevents a workflow from silently resolving different
dependencies. If `pyproject.toml` and `uv.lock` disagree, the job should fail so
the lockfile can be corrected and reviewed.

## Choosing triggers

Select the narrowest events that match the workflow's purpose:

| Trigger | Appropriate use |
| --- | --- |
| `pull_request` | Validate proposed changes before merge. |
| `push` | Validate or publish commits on selected branches or tags. |
| `workflow_dispatch` | Permit an authorised manual run. |
| `schedule` | Run periodic maintenance checks; not a substitute for pull-request checks. |

Use branch and path filters to avoid unnecessary work, but ensure they cannot
skip a required check after a relevant configuration change. Dependency files,
workflow files, and shared configuration often affect more jobs than their
names initially suggest.

Avoid running the same expensive job for both a feature-branch push and its
pull request unless both results are required.

## Reading a workflow result

Open the repository's **Actions** tab, select a workflow run, then select its
failed job and step. Begin with the first meaningful error rather than the
final summary line.

Common causes include:

- A test, lint, formatting, typing, or documentation failure.
- `uv.lock` being absent or inconsistent with `pyproject.toml`.
- A path or filename differing by case; Linux runners use case-sensitive
  filesystems.
- Code relying on a local file, environment variable, or uncommitted change.
- Missing permissions, secrets, or access to an external service.
- A temporary third-party service or network failure.

Reproduce the failing command locally using the locked environment before
changing the workflow:

```bash
uv sync --locked
uv run --locked <failing-command>
```

Do not repeatedly rerun an intermittent failure without investigating it.
Unreliable tests and network dependencies reduce confidence in every workflow
result.

## Permissions and secrets

Set workflow permissions explicitly and grant only what a job requires. An
ordinary test job generally needs only:

```yaml
permissions:
  contents: read
```

The documentation deployment needs additional Pages and identity-token
permissions, which are already scoped in `docs.yaml`.

Store credentials in GitHub Actions secrets or protected environments, never
in workflow YAML, source code, logs, or committed configuration. Avoid printing
environment variables that may contain secrets.

Pull requests from forks do not normally receive repository secrets. Do not
weaken this protection merely to make a contribution workflow convenient.
Workflows that handle untrusted pull-request code must not combine it with
powerful tokens or sensitive RDS credentials.

## Research data and DVC

The ordinary CI workflow should not require the complete dataset, an RDS mount,
or DVC credentials. Tests should use small synthetic or approved fixtures.

If a separate workflow must reproduce a DVC pipeline:

- Use an approved self-hosted or institutionally managed runner.
- Apply the required information-governance controls.
- Restrict the workflow and environment to trusted branches and reviewers.
- Use read-only access unless the workflow genuinely needs to publish outputs.
- Prevent sensitive data, filenames, paths, and credentials from entering logs
  or artifacts.
- Do not assume that a GitHub-hosted runner is approved for research data.

Configuring an RDS or cloud remote is not itself authorisation to expose data
to GitHub Actions.

## Matrices and supported Python versions

A matrix can run the same job against several Python versions or operating
systems:

```yaml
strategy:
  matrix:
    python-version: ["3.11", "3.12"]

steps:
  - name: Install Python
    run: uv python install ${{ matrix.python-version }}
```

Only add versions the project claims to support and can resolve through its
lockfile. A matrix multiplies runner time, so use it where platform or version
compatibility is part of the supported interface.

## Branch protection

After the CI workflow is stable, configure a GitHub ruleset for protected
branches. A ruleset can require:

- Changes to arrive through pull requests.
- One or more approving reviews.
- Selected Actions jobs to pass before merge.
- Conversations to be resolved.
- Force pushes and branch deletion to be blocked.

Use the stable job name as the required status check. Renaming that job may
require updating the repository ruleset.

## Updating actions safely

Reusable actions are third-party code executed by the workflow. Use actions
from trusted maintainers, grant minimal permissions, and review version updates
like dependency updates. Automated dependency-update pull requests can help,
but their changes should still be reviewed and allowed to complete checks.

Avoid adding an action when a short, clear shell command using an already
installed tool would be easier to audit.

## Recommended workflow design

- Give workflows, jobs, and steps descriptive names.
- Keep jobs focused and make dependencies explicit with `needs`.
- Recreate environments from `uv.lock` rather than relying on runner state.
- Use caches only to improve speed; correctness must not depend on a warm cache.
- Treat warnings as failures where the project has chosen strict validation.
- Upload only useful, non-sensitive artifacts with an appropriate retention
  period.
- Add comments for security-sensitive or non-obvious choices.
- Keep deployment separate from pull-request validation.
- Test workflow changes in a branch before relying on them for protection.

## Further reading

- [Understanding GitHub Actions](https://docs.github.com/en/actions/about-github-actions/understanding-github-actions)
- [Workflow concepts](https://docs.github.com/en/actions/concepts/workflows-and-actions/workflows)
- [Workflow syntax](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax)
- [Events that trigger workflows](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows)
- [Security for GitHub Actions](https://docs.github.com/en/actions/security-for-github-actions)
- [Using uv with GitHub Actions](https://docs.astral.sh/uv/guides/integration/github/)
