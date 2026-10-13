# Publishing documentation with GitHub Pages

[GitHub Pages](https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages)
hosts *free* static websites directly from GitHub repositories. In this project,
MkDocs converts the [Markdown](https://www.markdowntutorial.com/) files in `docs/` into a static website, and a
GitHub Actions workflow publishes the generated site to GitHub Pages.

The following describes this workflow.  Note that this will only happen when the `main` git branch changes
(you don't want development code to update the main public-facing website).

```text
Push to main
    ↓
GitHub Actions checks out the repository
    ↓
uv recreates the locked documentation environment
    ↓
MkDocs builds the static site
    ↓
GitHub Actions uploads and deploys the Pages artifact
    ↓
Documentation is available at <owner>.github.io/<repository>/
```

No generated website files need to be committed to the repository.

## Repository visibility and access

With GitHub Free or GitHub Free for organizations, the repository must be
**public** to use GitHub Pages. Paid GitHub plans may also support Pages for
private repositories. Check the current
[GitHub Pages availability](https://docs.github.com/en/pages/getting-started-with-github-pages/creating-a-github-pages-site#who-can-use-this-feature)
before relying on private-repository support.

!!! warning "The published site is public"
    A GitHub Pages site is normally publicly accessible even when its source
    repository is private. Never publish credentials, private URLs,
    identifiable research data, or other sensitive information in the
    documentation or generated site.

Administrator or maintainer access to the repository is required to configure
its Pages publishing source.

## Before enabling GitHub Pages

Confirm that the MkDocs settings describe the new repository:

```yaml
site_name: Your Project
site_url: https://<owner>.github.io/<repository>/
repo_url: https://github.com/<owner>/<repository>
```

For a project site, retain the repository name and trailing slash in
`site_url`. For example, RC4R uses:

```yaml
site_url: https://ICR-Computational-Imaging.github.io/RC4R/
```

Build the documentation locally before configuring deployment:

```bash
uv sync
uv run mkdocs build --strict
```

The strict build fails on warnings, helping detect missing navigation pages or
invalid configuration before publishing.

GitHub Actions should recreate the environment from a committed lockfile. If
`uv.lock` does not exist yet, create and commit it:

```bash
uv lock
git add pyproject.toml uv.lock
git commit -m "Lock Python dependencies"
```

## Editing documentation

Documentation pages are written in
[Markdown](https://www.markdowntutorial.com/) and stored under `docs/`. Create
one Markdown file for each page, using subdirectories to group related topics.

Add each reader-facing page to the `nav` section of `mkdocs.yaml` so that it is
discoverable through the site's navigation. This project currently uses the
following navigation structure:

```yaml title="mkdocs.yaml"
--8<-- "mkdocs.yaml:navigation"
```

This includes a top-level **Home** page and a **General** section containing a number of
subpages. YAML indentation determines which pages belong to a section.

Preview the documentation while editing with:

```bash
uv run mkdocs serve
```

MkDocs prints a local address similar to:

```text
INFO - Serving on http://127.0.0.1:8000/RC4R/
```

Open the printed address rather than opening files under `site/` directly.
MkDocs watches the source files and reloads the browser preview after changes
are saved.

The local server is for development only. Before committing documentation,
also run a strict build to detect warnings that might prevent publication:

```bash
uv run mkdocs build --strict
```

## Configure the repository

On GitHub:

1. Open the repository.
2. Select **Settings**.
3. Under **Code and automation**, select **Pages**.
4. Under **Build and deployment**, set **Source** to **GitHub Actions**.

This tells GitHub that a workflow will build and upload the website. GitHub
does not need a dedicated `gh-pages` branch when this approach is used. See
GitHub's guide to
[configuring a publishing source](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site).

## Add the deployment workflow

The GitHub Action deployment workflow is found in `.github/workflows/docs.yml`.

The workflow follows GitHub's recommended Pages process:

1. `actions/checkout` downloads the repository onto a temporary runner.
2. `astral-sh/setup-uv` installs uv and enables dependency caching.
3. `uv sync --locked` installs the committed documentation environment.
4. MkDocs builds the site into `site/` and treats warnings as failures.
5. `actions/upload-pages-artifact` packages the generated static files.
6. `actions/deploy-pages` publishes that artifact to GitHub Pages.

The `pages: write` and `id-token: write` permissions are required for the
deployment action. The `github-pages` environment records deployments and can
be given branch protection rules. GitHub documents these requirements in
[Using custom workflows with GitHub Pages](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages).

The workflow runs automatically only after documentation-related files are
pushed to `main`. The `workflow_dispatch` trigger also adds a **Run workflow**
button on the repository's **Actions** page for manual deployments.

## Publish the site

Commit the workflow and push it through the normal review process. After it is
merged into `main`:

1. Open the repository's **Actions** tab.
2. Select the **Documentation** workflow.
3. Confirm that both the build and deploy jobs complete successfully.
4. Open **Settings → Pages** to find the published URL.

The default project-site URL is:

```text
https://<owner>.github.io/<repository>/
```

Future qualifying pushes to `main` rebuild and replace the published site
automatically. Contributors edit only the Markdown, configuration, and source
docstrings; GitHub Actions takes care of building and publishing the HTML.

## Pull requests and deployment safety

The deployment workflow above publishes only from `main`. Documentation from a
feature branch or pull request is not deployed to the public site.

Continuous integration can still run a strict MkDocs build for pull requests
without granting Pages deployment permissions. This validates proposed
documentation changes before they are merged while keeping publication tied to
the stable branch.

For additional control, configure a deployment protection rule for the
`github-pages` environment so that only `main` can deploy.

## Troubleshooting

### The workflow cannot find `uv.lock`

Create the lockfile locally with `uv lock`, commit it, and rerun the workflow.

### MkDocs reports a missing page

Check that every path under `nav` in `mkdocs.yaml` exists relative to `docs/`.
Run `uv run mkdocs build --strict` locally to reproduce the failure.

### The site has incorrect links or styling

Confirm that `site_url` contains the repository name and ends with `/`. Project
Pages sites are served beneath `/<repository>/`, not at the domain root.

### The workflow succeeds but no site is available

Confirm that **Settings → Pages → Source** is set to **GitHub Actions**,
then inspect the deployment job and the `github-pages` environment.

### A repository was made private

On GitHub Free, changing the repository to private unpublishes its Pages site.
Make the repository public again or use a plan and organization policy that
support Pages for private repositories.

## Further reading

- [What is GitHub Pages?](https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages)
- [Creating a GitHub Pages site](https://docs.github.com/en/pages/getting-started-with-github-pages/creating-a-github-pages-site)
- [Configuring a publishing source](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site)
- [Using custom GitHub Actions workflows](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages)
- [Using uv in GitHub Actions](https://docs.astral.sh/uv/guides/integration/github/)
- [MkDocs deployment documentation](https://www.mkdocs.org/user-guide/deploying-your-docs/)
