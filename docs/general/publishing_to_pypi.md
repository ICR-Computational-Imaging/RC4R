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

### Create a new project using Trusted Publishing

You do not create an empty project separately or upload files through the
browser. The first successful package upload creates the project. For this
guide's recommended GitHub route, prepare a **pending publisher** first:

1. Sign in to the target registry and open **Publishing** in your account
   settings. For PyPI, this is [account publishing settings](https://pypi.org/manage/account/publishing/);
   for TestPyPI, use [its separate publishing settings](https://test.pypi.org/manage/account/publishing/).
2. Find the form for adding a pending publisher and select **GitHub Actions**.
3. Enter the project name from `[project].name`, the repository owner and
   name, the workflow filename `publish.yaml`, and the environment name:
   `pypi` for PyPI or `testpypi` for TestPyPI.
4. Select **Add** and confirm that the pending publisher is listed. The full
   field values for this repository are shown in step 5 below.
5. Complete steps 4–6 to configure GitHub, then run the first publication in
   step 7 for TestPyPI and step 8 for PyPI. Successful publication creates
   the project and converts the pending publisher to a normal publisher.
6. Reopen **Your projects** and the public project page to confirm the project
   and its first release are present on that registry.

Registering a pending publisher does not reserve the name or create the
project yet. If someone registers it before your first upload, you must choose
another available name. See [PyPI's new-project instructions](https://docs.pypi.org/trusted-publishers/creating-a-project-through-oidc/).

For the token-based alternative at the end of this guide, the first authorised
upload also creates a new project; a separate empty-project registration is
not required. For a project you already manage, use its **Manage → Publishing**
settings instead of creating a pending publisher.

**Expected outcome:** you can sign in to both registries and know whether to
configure an existing project or a pending publisher for a new one. The project
itself is created when its first upload succeeds. TestPyPI has its own accounts
and package records; see [the TestPyPI guide](https://packaging.python.org/en/latest/guides/using-testpypi/)
and [PyPI account help](https://pypi.org/help/).

## 3. Build and check the release locally

**Responsible: maintainer. Location: a checkout of the reviewed release tag.**

Use bumpversion in a release-preparation PR to set the agreed version. Do not
edit `VERSION` independently of that policy. Once the PR has merged into
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

## 5. Register Trusted Publishers

**Responsible: package owner. Location: PyPI and TestPyPI account settings.**

Trusted Publishing allows the named GitHub workflow to obtain a short-lived
publishing credential. You do not create or store a PyPI API-token secret for
this route.

For a new project, open **Publishing** in your account settings and add a
pending GitHub publisher. For an existing project, open **Your projects →
Manage → Publishing** and add its publisher there.

Register these values separately on both registries:

| Field | PyPI | TestPyPI |
| --- | --- | --- |
| Project name, for a new project | `dermapred` | `dermapred`, if available |
| Repository owner | `ICR-Computational-Imaging` | `ICR-Computational-Imaging` |
| Repository name | `RC4R` | `RC4R` |
| Workflow filename | `publish.yaml` | `publish.yaml` |
| Environment name | `pypi` | `testpypi` |

Use your actual names if they differ. The workflow field is the filename,
not `.github/workflows/publish.yaml` and not the workflow's display name.
If you use a different project name for testing, change the package's build
metadata in a separate test checkout; the registration must match the built
distribution's name.

**Expected outcome:** each registry lists its publisher. For a new project,
the first successful upload creates the project; a pending publisher does not
reserve the name. See [creating a project through Trusted Publishing](https://docs.pypi.org/trusted-publishers/creating-a-project-through-oidc/)
and [adding a publisher to an existing project](https://docs.pypi.org/trusted-publishers/adding-a-publisher/).

## 6. Add the publishing workflow

**Responsible: contributor prepares the PR; maintainer reviews and merges it.**

The example below is stored in `docs/examples/publish.yaml`. It is a template,
not an enabled GitHub workflow. Copy it to `.github/workflows/publish.yaml`
after configuring the environments and publishers, then review it through a PR.

```bash
cp docs/examples/publish.yaml .github/workflows/publish.yaml
git add .github/workflows/publish.yaml
git commit -m "Add reviewed Python package publishing workflow"
```

Push the branch and open the PR using the repository's normal workflow. The
publishing workflow must be present on GitHub's default branch before manual
runs are available. Include it in the reviewed commit before creating the
release tag that you will use for publication.

The template uses a manual run against a version tag, with TestPyPI selected
by default. It checks that the tag matches `VERSION`, runs synthetic tests,
builds distributions, and checks the installed wheel. A separate publication
job receives the built files and the `id-token: write` permission needed for
Trusted Publishing. See [uv's GitHub Actions publishing example](https://docs.astral.sh/uv/guides/integration/github/#publishing-to-pypi).

```yaml
--8<-- "docs/examples/publish.yaml"
```

**Expected outcome:** **Publish Python package** appears in the Actions tab.
Pushing a tag alone does not publish anything with this manual template.

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

## Alternative: publish using a GitHub secret

**Responsible: package owner creates the token; repository admin stores it.**

Use this route if Trusted Publishing is not being used. A PyPI API token is
different from a GitHub token and different from the account password. PyPI
and TestPyPI require separate tokens.

On the target registry, open **Account settings → API tokens → Add API token**.
Give it a descriptive name. Use project scope for an existing project; for
a first upload, an account-wide token may be needed because the project does
not yet exist. Replace that with a project-scoped token afterwards. Copy the
token when displayed; see [PyPI API-token help](https://pypi.org/help/#apitoken).

For an environment secret:

1. Open the GitHub repository's **Settings → Environments**.
2. Choose `pypi` or `testpypi`, matching the token's registry.
3. Under **Environment secrets**, choose **Add environment secret**.
4. Name it `PYPI_API_TOKEN` and paste the complete token as its value.

Using the same secret name in both environments is fine: each environment
holds its own value. The job must declare the environment to access its secret.

For a repository secret instead, open **Settings → Secrets and variables →
Actions → New repository secret**. Use `PYPI_API_TOKEN` for PyPI and
`TEST_PYPI_API_TOKEN` for TestPyPI, then select the matching secret in the job.
See [GitHub's secret setup instructions](https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/use-secrets).

For the environment-secret route, replace the template's publication step with:

```yaml
- name: Publish using an environment token
  env:
    UV_PUBLISH_TOKEN: ${{ secrets.PYPI_API_TOKEN }}
    REGISTRY: ${{ inputs.registry }}
  run: |
    case "$REGISTRY" in
      testpypi)
        uv publish --trusted-publishing never \
          --publish-url https://test.pypi.org/legacy/ dist/*
        ;;
      pypi)
        uv publish --trusted-publishing never dist/*
        ;;
      *) exit 1 ;;
    esac
```

Remove `id-token: write` from that job when using only the token route. Keep
the environment and its review rules. Store the token in GitHub settings,
not in YAML, `.env` files committed to Git, documentation, or shell commands.
GitHub stores the secret; the workflow references its name. uv reads the value
through `UV_PUBLISH_TOKEN`. See [uv authentication for publishing](https://docs.astral.sh/uv/guides/publish/#publishing-your-package).

**Expected outcome:** the publication job receives the target environment's
token and uploads to its registry. Adding the secret alone does not publish.

## If something goes wrong

| Result | Check |
| --- | --- |
| Workflow is not listed | The enabled file must be in `.github/workflows/` on the default branch. |
| Jobs are skipped | Trigger the workflow using a reviewed `v` tag, not a branch. |
| Tag/version mismatch | Compare the tag name with `VERSION` in the tagged commit. |
| Waiting for approval | The environment's reviewer must approve the job. |
| Trusted Publisher authentication fails | Check registry, owner, repo, workflow filename, environment, and `id-token: write`. |
| Token authentication fails | Check the target registry, token scope, secret name, and job environment. |
| Package name is unavailable | Choose an available name and update metadata and publisher registration. |
| Filename already exists | Publish a new version rather than replacing a file. |
| TestPyPI cannot find a dependency | Install dependencies from PyPI, then use `--no-deps` for the TestPyPI package. |
| Inference reports a missing manifest | Supply the selected model manifest; publication of code does not create it. |

**Expected outcome:** the released package version installs through pip, and
its model bundle and usage instructions are identifiable from the release notes.
