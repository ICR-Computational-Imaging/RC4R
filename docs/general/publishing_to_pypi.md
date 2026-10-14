# Publishing a Python package: a walkthrough

This guide takes a maintainer from a locally built package to a release that
other people can install using pip. The example uses `dermapred` version
`0.1.0`; replace the name and version when adapting this template.

For issue approval, release branches, bumpversion, and tagging the reviewed
commit, start with the [development workflow](development_workflow.md).
For installing the package and running images, see the
[inference guide](../dermapred/inference.md).

## What each tool does

| Tool or service | Purpose |
| --- | --- |
| pip | Installs Python packages into a Python environment. |
| PyPI | Hosts published packages that pip can download. |
| TestPyPI | A separate practice registry for checking publication. |
| uv | Builds this project's distributions and uploads them. |
| GitHub Actions | Runs the build, tests, and publication commands. |
| GitHub Release | Holds release notes and separately distributed model files. |

Publishing the Python package does not upload model files. In this template,
the wheel supplies inference code, while an explicit manifest selects the
weights and calibrator. See [model releases](../dermapred/model_download.md).
Package tests use synthetic inputs; publication does not require held-out data.

## 1. Get pip working locally

**Responsible: contributor or maintainer. Location: your terminal.**

Check that Python and its pip command are available:

```bash
python3 --version
python3 -m pip --version
```

On Windows, `py` can replace `python3`. Use the interpreter you intend to run
the package with; this project requires Python 3.11 or newer. Calling
`python -m pip` keeps pip associated with that particular interpreter.

Create an environment for installation checks, separate from the development
environment. Run these commands from the repository root:

```bash
python3 -m venv .venv-pip-check
```

Activate it on macOS or Linux:

```bash
source .venv-pip-check/bin/activate
```

Or in Windows PowerShell:

```powershell
.\.venv-pip-check\Scripts\Activate.ps1
```

Then check pip in the activated environment:

```bash
python -m pip install --upgrade pip
python -m pip --version
```

If Python reports that pip is missing, try `python -m ensurepip --upgrade`.
If your Python installation lacks `venv` or `ensurepip`, use its platform's
installation instructions. With uv, an alternative is
`uv venv --seed .venv-pip-check`, then activate it as above.

**Expected outcome:** pip's reported path points into `.venv-pip-check`.
Run `deactivate` when finished. Keep the check environment out of Git; add
`.venv-pip-check/` to `.gitignore` if it is not already ignored.
See the [Python Packaging installation guide](https://packaging.python.org/en/latest/tutorials/installing-packages/).

## 2. Create the accounts and check the project name

**Responsible: the package owner or maintainer. Location: your browser.**

Create and verify accounts separately on [PyPI](https://pypi.org/account/register/)
and [TestPyPI](https://test.pypi.org/account/register/). Set up the required
two-factor authentication and retain your recovery information.

Agree who owns the package and who can publish subsequent releases. A GitHub
repository name and a PyPI project name are separate: this repository is
`RC4R`, while `[project].name` in `pyproject.toml` is `dermapred`. The name in
your package metadata determines which PyPI project receives the upload.

### Check whether the project already exists

Check both registries before setting up publication:

1. Open [the PyPI project page for dermapred](https://pypi.org/project/dermapred/).
   For another package, replace `dermapred` in the address with its project name.
2. If a project page appears, that name already exists on PyPI. Read its
   description and maintainer information to identify whether it is yours.
3. Sign in and open **Your projects** from your account menu. If the project
   appears there, select **Manage** to configure it. If it belongs to your
   organisation but you cannot manage it, ask its owner to add your account
   as an owner or maintainer before attempting publication.
4. Repeat these checks on [TestPyPI](https://test.pypi.org/project/dermapred/).
   Access to the PyPI project does not grant access to the TestPyPI project.

If the name belongs to someone else's project, choose a different package
name and update `[project].name` before building. A page-not-found response
means there is no visible project at that address; it does not guarantee that
the name can be registered. PyPI can reject prohibited or conflicting names,
including names with no visible releases. See [PyPI's project-name guidance](https://pypi.org/help/#project-name).

### Create a new project with the first upload

You do not create an empty project separately or upload files through the
browser. The first successful package upload creates the project using the
name in `[project].name` in `pyproject.toml`.

For a new project, create an account-wide API token and store it in GitHub as
explained in step 5. Once the first upload has created the project, replace
that token with one scoped to the project. For an existing project, use a
project-scoped token belonging to an owner or maintainer with upload access.

After publishing, reopen **Your projects** and the public project page on the
target registry to confirm the project and release are present. An API token
does not reserve a project name; the registry checks it when the first upload
is attempted. See [PyPI API-token help](https://pypi.org/help/#apitoken).

**Expected outcome:** you can sign in to both registries and know whether the
project already exists. The first successful upload creates a new project.
TestPyPI has its own accounts, projects, and API tokens; see the
[TestPyPI guide](https://packaging.python.org/en/latest/guides/using-testpypi/).

## 3. Build and check the release locally

**Responsible: maintainer. Location: a checkout of the reviewed release tag.**

Contributors set the approved development target on their issue branches
using `bumpversion major`, `minor`, or `patch`. The maintainer uses
`uv run bumpversion release` in a release-preparation PR to remove the
development suffix; contributors must not run that command. Do not edit
`VERSION` independently of that policy. Once the release PR has merged into
`main`, tag its approved commit as described in the development workflow.

For `v0.1.0`, create a fresh release checkout:

```bash
git fetch origin --tags
git worktree add --detach ../RC4R-release-0.1.0 v0.1.0
cd ../RC4R-release-0.1.0
uv build
```

**Expected outcome:** `dist/` contains a wheel such as
`dermapred-0.1.0-py3-none-any.whl` and a source archive such as
`dermapred-0.1.0.tar.gz`. Build in a fresh folder so older versions cannot be
uploaded accidentally. See [uv's package publishing guide](https://docs.astral.sh/uv/guides/publish/).

Create and activate a fresh pip-check environment in this checkout using step 1:

```bash
python -m pip install dist/dermapred-0.1.0-py3-none-any.whl
python -m pip show dermapred
dermapred --help
python -c "from dermapred.inference import Predictor; print('Inference API imports successfully')"
```

Use the actual filenames and version produced by your build. Also run the
synthetic inference tests before release and, when the model bundle is
available, check the installed package with a known input image. An import
check alone does not verify model downloads or prediction behaviour.

**Expected outcome:** pip reports the release version, the CLI displays its
help, and the API imports without installing the training dependency group.

## 4. Configure GitHub environments

**Responsible: repository admin. Location: GitHub repository settings.**

Open **Settings → Environments → New environment**. Create two environments
with the exact names `testpypi` and `pypi`.

For `pypi`, add the maintainer or admin as a required reviewer where the
repository's GitHub plan supports it. Configure deployment branch/tag rules
to allow release tags matching `v*`. Configure `testpypi` similarly if you
want approval for practice uploads too.

**Expected outcome:** a publication job names its target environment and waits
for any configured approval. These settings are configured on GitHub, not by
committing YAML. See [GitHub environment protection rules](https://docs.github.com/en/actions/reference/workflows-and-actions/deployments-and-environments).

## 5. Create API tokens and add GitHub secrets

**Responsible: package owner creates the tokens; repository admin stores them.**

The workflow publishes using API tokens stored as **GitHub environment
secrets**. It uses the secret named `PYPI_API_TOKEN` from the selected `pypi`
or `testpypi` environment. Each environment holds a different token value.

A PyPI API token is different from a GitHub token and from your account
password. Create separate tokens for PyPI and TestPyPI.

### Create each registry token

1. Sign in to [PyPI account settings](https://pypi.org/manage/account/) or
   [TestPyPI account settings](https://test.pypi.org/manage/account/).
2. Open **API tokens → Add API token**.
3. Give it a descriptive name, such as `RC4R GitHub publishing`.
4. For an existing project, select the scope for `dermapred`. For the first
   upload of a project that does not exist yet, select **Entire account**.
5. Create the token and copy the complete value, including its `pypi-` prefix.
   The token is shown only once.
6. Repeat on the other registry. A PyPI token cannot authenticate to TestPyPI.

After the first upload creates the project, create a project-scoped token,
replace the GitHub secret with it, then revoke the old account-wide token.
See [PyPI API-token help](https://pypi.org/help/#apitoken).

### Store each token in GitHub

1. Open the repository's **Settings → Environments**.
2. If **pypi** is listed, select it. If it is missing, choose **New environment**,
   enter `pypi`, then select **Configure environment**. The environments are
   created by you in step 4; they are not present by default.
3. Under **Environment secrets**, choose **Add environment secret**.
4. Enter `PYPI_API_TOKEN` as the name and paste the PyPI token as its value.
5. Save the secret.
6. Return to **Settings → Environments** and open **testpypi**. If it is
   missing, create it with **New environment → testpypi → Configure environment**.
   Add another environment secret named `PYPI_API_TOKEN`, using the TestPyPI
   token as its value.

| GitHub environment | Secret name | Token issued by |
| --- | --- | --- |
| `pypi` | `PYPI_API_TOKEN` | PyPI |
| `testpypi` | `PYPI_API_TOKEN` | TestPyPI |

Use **Environment secrets** for this workflow, rather than adding both tokens
as repository secrets. The selected environment determines which value the
publication step receives. See [GitHub's secret setup instructions](https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/use-secrets).

The workflow references the secret by name and passes it to uv through
`UV_PUBLISH_TOKEN`. It disables Trusted Publishing explicitly and requires no
publisher registration or `id-token: write` permission. Keep the token value
in GitHub settings; do not put it in repository files or terminal commands.
See [uv publishing authentication](https://docs.astral.sh/uv/guides/publish/#publishing-your-package).

**Expected outcome:** both environments list a secret named `PYPI_API_TOKEN`.
GitHub hides the values. Adding these secrets does not publish anything; a
maintainer must start the tagged workflow manually.

## 6. Review and enable the publishing workflow

**Responsible: contributor prepares the PR; maintainer reviews and merges it.**

The workflow is included in `.github/workflows/publish.yaml`. Configure the
GitHub environments and API-token secrets from steps 4–5, then review and
merge the workflow through a PR. When adapting another project, the original
starting template is also available in `docs/examples/publish.yaml`.

The workflow must be present on GitHub's default branch before manual runs
are available. Include it in the reviewed commit before creating the release
tag that you will use for publication. You create and push that tag manually,
as described in the [development workflow](development_workflow.md).
The publishing workflow does not bump versions, create tags, or commit changes.

Run it manually against a version tag, with TestPyPI selected by default. It
checks that the tag matches `VERSION`, runs synthetic tests, builds
distributions, and checks the installed wheel outside the source checkout.
GitHub records the source tag and commit on the run, and the run name shows
the target registry. The distributions are attached as the
`python-distributions` artifact for review and transfer to the publishing job.

A separate publication job receives those built files, names the selected
GitHub environment, and passes its `PYPI_API_TOKEN` secret to uv only in the
publication step. It waits for any reviewers configured on that environment.
Reviewers must be configured in GitHub settings; the YAML alone does not require
approval. See [uv's GitHub Actions publishing example](https://docs.astral.sh/uv/guides/integration/github/#publishing-to-pypi).

```yaml
--8<-- ".github/workflows/publish.yaml"
```

**Expected outcome:** **Publish Python package** appears in the Actions tab
once the workflow is on the default branch. Pushing a tag alone does not
publish anything; you start the publication run explicitly.

## 7. Publish to TestPyPI first

**Responsible: maintainer. Location: your terminal and GitHub Actions.**

With GitHub CLI installed, authenticate once using `gh auth login`. Trigger
the workflow at the reviewed tag, replacing the example version if needed:

```bash
gh workflow run publish.yaml --ref v0.1.0 -f registry=testpypi
```

The `--ref` argument selects the tagged code; `registry` selects the destination.
Running it against a branch instead of a `v` tag skips the build and publication.
Open GitHub's **Actions** tab, select the run, check the tag, and approve its
environment if required. The final **Publish verified distributions** step is
the step that actually uploads the package.

**Expected outcome:** the version appears at
`https://test.pypi.org/project/dermapred/0.1.0/` when the job succeeds.

In a fresh pip-check environment, get the runtime dependencies from ordinary
PyPI, then install only your package from TestPyPI:

```bash
python -m pip install torch numpy pillow
python -m pip install --index-url https://test.pypi.org/simple/ \
  --no-deps dermapred==0.1.0
python -m pip show dermapred
dermapred --help
```

This avoids depending on TestPyPI to contain PyTorch and every transitive
dependency. Repeat the installed-package inference check when your model
bundle is available. See [installing from TestPyPI](https://packaging.python.org/en/latest/guides/using-testpypi/).

## 8. Publish the approved version to PyPI

**Responsible: maintainer; configured reviewer approves the publication job.**

After the TestPyPI check succeeds, run the same reviewed tag with the production
destination:

```bash
gh workflow run publish.yaml --ref v0.1.0 -f registry=pypi
```

Check the tag and target environment in the Actions run before approval.
The workflow rebuilds from the same tag for this run; it does not promote the
previous run's exact wheel. If exact artifact promotion is required, adapt the
workflow to retain and reuse the verified distributions.

**Expected outcome:** the version appears on PyPI. In a new environment, users
can install it with:

```bash
python -m pip install dermapred==0.1.0
python -m pip show dermapred
dermapred --help
```

Published distribution filenames cannot be reused for corrected files. Make a
new reviewed patch release, such as `0.1.1`, instead of replacing `0.1.0`.
Deleting a release does not make its filenames reusable. See [PyPI file-reuse help](https://pypi.org/help/#file-name-reuse).

## Maintain the publishing tokens

To replace a token, create its replacement on the same registry, edit
`PYPI_API_TOKEN` in the corresponding GitHub environment, and revoke the old
token after checking the replacement. Use project scope once the project exists.
No workflow edit is needed when a secret value changes.

## If something goes wrong

| Result | Check |
| --- | --- |
| Workflow is not listed | The enabled file must be in `.github/workflows/` on the default branch. |
| Jobs are skipped | Trigger the workflow using a reviewed `v` tag, not a branch. |
| Tag/version mismatch | Compare the tag name with `VERSION` in the tagged commit. |
| Waiting for approval | The environment's reviewer must approve the job. |
| Missing `PYPI_API_TOKEN` | Add the environment secret to the selected `pypi` or `testpypi` environment. |
| Token authentication fails | Check the target registry, token scope, secret name, and job environment. |
| Package name is unavailable | Choose an available name and update metadata and token scope. |
| Filename already exists | Publish a new version rather than replacing a file. |
| TestPyPI cannot find a dependency | Install dependencies from PyPI, then use `--no-deps` for the TestPyPI package. |
| Inference reports a missing manifest | Supply the selected model manifest; publication of code does not create it. |

**Expected outcome:** the released package version installs through pip, and
its model bundle and usage instructions are identifiable from the release notes.
