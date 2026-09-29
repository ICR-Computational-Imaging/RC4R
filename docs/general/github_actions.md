# Automation with GitHub Actions

## Purpose

[GitHub Actions](https://docs.github.com/en/actions) runs automated tasks in
response to repository *events* (e.g. push or pull request).
It can test proposed changes, apply quality checks, build documentation,
and publish approved outputs in a fresh environment.

Automation supports consistent project standards by running the same declared
process for every contributor. A successful workflow means only that its
configured steps passed; it does not replace review or establish scientific
validity.

GitHub reads workflow files ending in `.yml` or `.yaml` from:

```text
.github/workflows/
```

Other files in that directory, such as a README, are not executed.

> **Note**
> Ordinary GitHub Actions workflows should not access sensitive research data.
> Data processing should take place only on approved systems and storage, using DVC where appropriate for versioning and reproducibility.

## Core concepts

| Component | Purpose |
| --- | --- |
| Workflow | A complete YAML automation definition. |
| Event | An occurrence that starts a workflow, such as a push or pull request. |
| Job | A group of steps executed on one runner. |
| Runner | The temporary or managed computer that executes a job. GitHub offers different [`runners`](https://docs.github.com/en/actions/reference/runners/github-hosted-runners). |
| Step | One command or reusable action within a job. |
| Action | A reusable automation component referenced with `uses`. |
| Artifact | Files retained by a workflow or passed between jobs. |
| Secret | An encrypted value made available only in an authorised context. |

The normal flow is:

```text
Repository event → workflow → jobs → steps → results and artifacts
```

Jobs run independently unless
[`needs`](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#jobsjob_idneeds)
declares a dependency. Steps within one job run in order and share that job's workspace.

## Workflow standards

Workflows should:

- Have a clear purpose and descriptive workflow, job, and step names.
- Use events and branches that match the workflow’s purpose.
- Recreate environments from committed configuration and lockfiles.
- Grant the minimum permissions needed.
- Keep validation separate from deployment.
- Avoid exposing secrets or sensitive data to untrusted code.
- Produce logs that help contributors diagnose failures.
- Avoid relying on undeclared runner state or a warm cache.
- Use trusted, reviewed third-party actions.
- Be documented when their behaviour or security requirements are not obvious.

## Concrete example

The following worked example is the workflow used to build and publish the project
documentation. It contains more comments than a typical workflow so that each
important field is explained. Use descriptive names for workflows, `jobs`, and
`steps` so their purpose is clear in the GitHub Actions interface.

```yaml title=".github/workflows/docs.yaml"
--8<-- "docs.yaml:doc_action"
```

## Triggers

You can define which GitHub events trigger a workflow at the top of the file.

For example:

```yaml
on:  # <--- Define the events that start the workflow.
  push:  # <--- Run after changes are pushed.
    branches:  # <--- Limit the push event to selected branches.
      - main
  workflow_dispatch:  # <--- Also permit an authorised manual run.
```

Some useful events are found below but a complete list is available via
[GitHub Actions documentation](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows)

| Trigger | Appropriate use |
| --- | --- |
| `pull_request` | Validate a proposed change before merge. |
| `push` | Validate or publish selected branches or tags. |
| `workflow_dispatch` | Allow an authorised manual run. |
| `schedule` | Run periodic maintenance tasks. |

## Jobs

Jobs should group related operations with one clear purpose.
This makes failures easier to locate and prevents deployment from running when an
earlier check fails.

Some job (e.g. build and validation) should be designed to run safely for pull requests,
without deployment permissions or sensitive credentials. Others (e.g. deployment) may change
external state and should run only from an approved branch, tag, or protected environment.

A simple example is shown below (this example is illustrative only,
see [Concrete example](#concrete-example) for a working one).

```yaml
jobs:  # <--- Each entry below defines a separate job.
  build:  # <--- Unique identifier used by other jobs, for example in "needs".
    name: Build solution  # <--- Descriptive name shown in the GitHub Actions UI.
    runs-on: ubuntu-latest  # <--- Type of temporary runner used for this job.
    steps:  # <--- Operations run in order on the same runner.
      - name: Check out repository
        uses: actions/checkout@v7  # <--- "uses" runs an existing reusable action.

      - name: Install uv
        uses: astral-sh/setup-uv@v10  # <--- Some actions are developed by third-parties.

      - name: Run build setup
        run: bash src/build_setup.sh  # <--- "run" executes a terminal command.

      - name: Build solution
        run: |  # <--- The "|" symbol permits multiple terminal commands.
          uv sync --group build
          uv run python src/build.py

      - name: Upload build results
        uses: actions/upload-artifact@v4  # <--- Preserve files after this job ends.
        with:
          name: build-results  # <--- Name used to identify this artifact in later jobs.
          path: build_results/  # <--- File or directory to upload from the runner.

  validate:  # <--- A second job, running on a new runner and filesystem.
    name: Validate solution
    runs-on: ubuntu-latest
    needs: build  # <--- Start only after the build job succeeds.
    steps:
      - name: Check out repository
        uses: actions/checkout@v7  # <--- Repository files are not shared between jobs.

      - name: Install uv
        uses: astral-sh/setup-uv@v10  # <--- Tools must also be installed in each job.

      - name: Download build results
        uses: actions/download-artifact@v5  # <--- Retrieve files uploaded by build.
        with:
          name: build-results  # <--- Must match the uploaded artifact name.
          path: build_results/  # <--- Directory to create on this runner.

      - name: Validate solution
        run: |
          uv sync --group validate
          uv run python src/validate.py

  deploy:  # <--- Deployment is isolated from building and validation.
    name: Deploy solution
    runs-on: macos-latest  # <--- Different jobs can use different runner types.
    needs: validate  # <--- Start only after the validation job succeeds.
    steps:
      - name: Check out repository
        uses: actions/checkout@v7

      - name: Install uv
        uses: astral-sh/setup-uv@v10

      - name: Download validated build results
        uses: actions/download-artifact@v5
        with:
          name: build-results  # <--- Deploy the same artifact that was validated.
          path: build_results/

      - name: Deploy solution
        run: |
          uv sync --group deploy
          uv run python src/deploy.py
```

`needs` controls job order but does not transfer files.
The upload and download artifact actions move
`build_results/` between the otherwise independent job filesystems.
Similarly, each job must check out the repository and install the tools it uses.

## Permissions

`permissions` controls what the temporary `GITHUB_TOKEN` issued to each job can do through GitHub’s API.
Depending on the permissions granted, the token can be used to:

- Check out private repository contents.
- Create a release or tag.
- Upload packages.
- Comment on issues or pull requests.
- Publish to GitHub Pages.

A top-level `permissions` block defines the default permissions for every job in the workflow.
The following illustrates several available permissions. A real workflow should include only
those it requires:

```yaml
permissions:
  contents: write       # <--- Create commits, tags, or releases.
  pull-requests: write  # <--- Comment on or modify pull requests.
  issues: write         # <--- Create or update issues.
  pages: write          # <--- Publish to GitHub Pages.
  id-token: write       # <--- Request an OpenID Connect identity token.
```

Permissions do not control whether shell commands can read or write files on the temporary runner.

A job-level `permissions` block replaces the workflow-level permissions for that job. Any
permission omitted from that job-level block is set to `none` (not inherited from workflow),
so repeat every permission the job still requires.

```yaml
permissions:
  contents: read  # <--- Default for jobs without their own permissions block.

jobs: 
  build:    # <--- Inherits read permissions
    name: Build solution 
    runs-on: ubuntu-latest

  release:
    name: Create release
    runs-on: ubuntu-latest
    permissions:
      contents: write  # <--- Write access applies only to this job.
```

## Secrets

If a workflow needs a password, token, private key, or other credential to access an external service, package registry, or deployment platform, configure it as a GitHub [`secret`](https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/use-secrets) rather than hard-coding it. Never write sensitive data within workflow YAML, source code, committed configuration, artifacts, or logs.

`secrets` can be registered for a repository on GitHub by:

1. Opening the project **Settings** tab.
2. In the **Security** side-bar section, select **Secrets and variables**.
3. Click **Actions**.
4. Click **Secrets** tab.
5. Click **New repository secret**.
6. In the **Name** field, provide a name for the secret (e.g. `DEPLOY_TOKEN`).
7. In the **Secret** field, enter the value (e.g. password).
8. Click **Add secret**.

The secret can then be supplied to only the step that requires it:

```yaml
jobs:
  deploy:
    name: Deploy solution
    runs-on: ubuntu-latest

    steps:
      - name: Check out repository
        uses: actions/checkout@v7

      - name: Install uv
        uses: astral-sh/setup-uv@v10

      - name: Deploy
        env:
          DEPLOY_TOKEN: ${{ secrets.DEPLOY_TOKEN }}  # <--- Read the GitHub secret.
        run: |
          uv sync --group deploy
          uv run python src/deploy.py
```

The deployment script can read `DEPLOY_TOKEN` from the process environment.
It must not print or otherwise expose the value.
For example, `src/deploy.py` could have the following:

```python
import os


deploy_token = os.getenv("DEPLOY_TOKEN")

if not deploy_token:
    raise RuntimeError("DEPLOY_TOKEN is not configured")
```

> **Note**
> GitHub creates a `GITHUB_TOKEN` automatically.
> Custom secrets such as `DEPLOY_TOKEN` must be added through the repository or environment settings.


Secrets should be exposed only to the step or job that requires them.
Pull requests from forks do not normally receive repository secrets.
Do not weaken this protection merely to make a workflow convenient: 
untrusted code must not receive powerful tokens,
deployment authority, or sensitive storage credentials.

## Reproducible environments

Automation should install from committed declarations:

```bash
uv sync --locked
```

Run project tools through the same environment:

```bash
uv run --locked pytest
```

Caches may reduce download time but must not supply undeclared dependencies or
change results. A workflow should also succeed on a clean runner without an
existing cache.

## Version and platform matrices

A matrix can run one job with several supported versions or platforms:

```yaml
strategy:
  matrix:
    python-version: ["<version-one>", "<version-two>"]
```

Use a matrix only for versions and systems the project intends to support. Each
entry increases runner time and maintenance, so more combinations are not
automatically better.

## Read and diagnose failures

Open the repository's **Actions** tab, select the run, then inspect its first
failed job and meaningful error. Common causes include:

- A test, formatting, linting, typing, or documentation failure.
- An inconsistent or missing lockfile.
- A filename whose case differs between source and reference.
- Dependence on an uncommitted file or local environment variable.
- Missing permissions or credentials.
- An unavailable external service.

Reproduce the failing command locally with the locked environment:

```bash
uv sync --locked
uv run --locked <failing-command>
```

Do not repeatedly rerun an intermittent failure without investigating it.
Unreliable workflows reduce confidence in every result.

## Artifacts and logs

Upload artifacts only when they are useful for review, deployment, or diagnosis.
Choose an appropriate retention period and confirm that the files contain no
sensitive data, secrets, private paths, or unnecessarily large outputs.

Logs should make failures understandable without exposing confidential values.
Avoid printing complete environments, credentials, or raw research records.

## Branch protection

Once a workflow is stable, a repository ruleset can require its status check
before a protected branch is updated. Rules may also require pull requests,
reviews, and resolved conversations while blocking force pushes and branch
deletion.

Use stable, descriptive job names for required checks. Renaming a required job
may require updating the repository ruleset.

## Maintain third-party actions

An action is external code executed by the workflow. Use actions from trusted
maintainers, review updates, and grant minimal permissions. Follow the
repository's chosen policy for pinning actions to reviewed releases or commit
identifiers.

Automated dependency-update pull requests can identify new action versions,
but those updates still require review and successful checks. Prefer a short,
clear command using an installed project tool when it is easier to audit than
adding another action.

## Review checklist

Before merging a workflow change, confirm that:

- Its triggers match its stated purpose.
- Commands work from a clean, locked environment.
- Permissions are minimal and explicit.
- Secrets are unavailable to untrusted code.
- No sensitive data are uploaded or logged.
- Deployment is restricted to approved sources.
- Action versions have been reviewed.
- Failure messages will be understandable to contributors.
- The workflow has been tested safely on a branch where practical.

## Further reading

- [Understanding GitHub Actions](https://docs.github.com/en/actions/about-github-actions/understanding-github-actions)
- [Workflow concepts](https://docs.github.com/en/actions/concepts/workflows-and-actions/workflows)
- [Workflow syntax](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax)
- [Workflow triggers](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows)
- [Security for GitHub Actions](https://docs.github.com/en/actions/security-for-github-actions)
- [Using uv with GitHub Actions](https://docs.astral.sh/uv/guides/integration/github/)
