# Writing documentation with MkDocs

## Introduction

[MkDocs](https://www.mkdocs.org/) converts Markdown files into a static
documentation website. The source remains readable in GitHub, while the built
site adds navigation, search, syntax highlighting, and consistent styling.

This project uses:

- [MkDocs](https://www.mkdocs.org/) to build the site.
- [Material for MkDocs](https://squidfunk.github.io/mkdocs-material/) as the
  visual theme.
- [mkdocstrings](https://mkdocstrings.github.io/) to generate Python API
  reference material from source code and docstrings.
- [PyMdown Extensions](https://facelessuser.github.io/pymdown-extensions/) for
  features such as highlighted code, snippets, and collapsible notes.

The documentation process is:

```text
Markdown + Python docstrings + assets
                 ↓
            MkDocs build
                 ↓
        Static HTML website
                 ↓
            GitHub Pages
```

MkDocs builds documentation only. It does not execute the project's research
pipeline or publish the site by itself. Publishing is handled separately by
GitHub Actions.

## Documentation structure

The important paths are:

```text
RC4R/
├── mkdocs.yaml             # Site configuration and navigation
├── pyproject.toml          # Documentation dependencies
├── docs/
│   ├── index.md            # Site home page
│   ├── README.md           # Notes for contributors; excluded from the site
│   ├── assets/             # Images, diagrams, and other static files
│   ├── examples/           # Optional reusable documentation snippets
│   └── general/            # General guidance pages
└── site/                   # Generated website; do not edit or commit
```

All reader-facing source pages live below `docs/`. Paths used in
`mkdocs.yaml` are relative to that directory.

The root `README.md` and `docs/index.md` serve different purposes. The root
README provides a concise introduction on GitHub; `docs/index.md` is the home
page of the complete documentation site.

## Install the documentation environment

MkDocs and its plugins belong to the `docs` dependency group in
`pyproject.toml`. The default `dev` group includes this group, so normal project
setup is sufficient:

```bash
uv sync
```

To install only the documentation tools and the project's runtime
dependencies, use:

```bash
uv sync --no-default-groups --group docs
```

Run documentation commands through uv so that they use the locked project
environment:

```bash
uv run mkdocs --version
```

Do not install a separate global copy of MkDocs for this project. A global
version may use different plugins or behave differently from the version in
`uv.lock`.

## Preview the site locally

Start MkDocs from the repository root:

```bash
uv run mkdocs serve
```

MkDocs prints a local URL, commonly similar to:

```text
http://127.0.0.1:8000/RC4R/
```

Open the exact URL printed in the terminal. MkDocs watches the configuration,
Markdown, and assets and normally refreshes the browser after a saved change.
Stop the server with `Ctrl+C`.

Do not open generated `site/index.html` directly in a browser or serve `site/`
with a generic file server. This project uses directory-style URLs, and bypassing
the MkDocs development server can produce directory listings or incorrect
links.

## Create a page

Create a Markdown file below `docs/`. Use a descriptive lowercase filename;
hyphens or underscores are both supported, but remain consistent within a
section. For example:

```text
docs/general/reproducibility.md
```

Begin the page with one clear level-one heading:

```markdown title="docs/general/reproducibility.md"
# Reproducibility

This page explains how to reproduce the analysis.

## Environment

Describe the required environment here.
```

Use headings in order and avoid skipping directly from `#` to `###`. Keep
instructions close to the commands they explain, and test commands from a
fresh environment where practical.

### Add the page to navigation

Register each reader-facing page in the `nav` section of `mkdocs.yaml`:

```yaml
nav:
  - Home: index.md
  - General:
      - Reproducibility: general/reproducibility.md
```

The text before the colon is the navigation label. The path after it is
relative to `docs/`. YAML indentation determines the hierarchy, so use spaces
consistently and do not use tabs.

A page can build without appearing in `nav`, but readers may have difficulty
finding it and a strict build may warn that it is omitted. The existing
navigation is marked as a named snippet in `mkdocs.yaml`, allowing another page
to display it without maintaining a duplicate.

## Write Markdown content

Standard Markdown supports headings, paragraphs, emphasis, lists, links,
tables, quotations, and code. Prefer plain Markdown over raw HTML so pages
remain readable on GitHub.

### Links

Use relative paths for pages within the documentation:

```markdown
[DVC guidance](dvc.md)
[Project home](../index.md)
```

Link to the Markdown source path, not the generated `.html` path. MkDocs
converts the destination during the build and can warn about invalid links.

Use descriptive link text instead of phrases such as “click here”. For
external references, link to the authoritative project or specification where
possible.

### Images and other assets

Store shared images under `docs/assets/`. From a page in `docs/general/`, embed
an image with:

```markdown
![Description of the diagram](../assets/dvc-overview.svg)
```

The description is alternative text for readers who cannot see the image.
Avoid placing sensitive data, participant information, or private URLs in
screenshots and diagrams. Prefer SVG for diagrams and PNG or JPEG for raster
images.

### Code blocks

Specify the language after the opening fence to enable syntax highlighting:

````markdown
```python title="example.py"
def answer() -> int:
    return 42
```
````

The configured Material features add a copy button and support titled and
annotated code blocks. See the
[Material code-block reference](https://squidfunk.github.io/mkdocs-material/reference/code-blocks/)
for the available options.

### Notes and warnings

Use an admonition when information genuinely needs to stand apart from the
main instructions:

```markdown
!!! warning "Sensitive data"
    Never include identifiable research data in the documentation site.
```

Indent the admonition body by four spaces. Available styles include `note`,
`info`, `tip`, `warning`, `danger`, and `example`. The
[admonition reference](https://squidfunk.github.io/mkdocs-material/reference/admonitions/)
contains further examples.

## Reuse content with snippets

The `pymdownx.snippets` extension can include content from another file. This
avoids manually copying configuration examples that would otherwise become
outdated.

Mark a named section in the source file using comments appropriate to that
file. The navigation section in `mkdocs.yaml` uses:

```yaml
# --8<-- [start:navigation]
nav:
  # Navigation entries
# --8<-- [end:navigation]
```

Include that section in a fenced code block with:

````markdown
```yaml title="mkdocs.yaml"
;--8<-- "mkdocs.yaml:navigation"
```
````

The leading semicolon above escapes the example in this guide; omit it in the
page that should perform the inclusion. The configured snippet base paths are
`mkdocs.yaml` and `docs/examples`.

Prefer named sections to line-number ranges because named sections remain
correct when lines are added or removed. See the
[PyMdown snippets reference](https://facelessuser.github.io/pymdown-extensions/extensions/snippets/)
for the complete syntax.

## Generate Python API documentation

The `mkdocstrings` plugin searches the repository's `src/` directory for
Python modules. To render the documentation for a module, place a directive in
a Markdown page:

```markdown
::: dermapred
```

A more focused page can address a submodule or object:

```markdown
::: dermapred.inference
```

The referenced module must be importable, and its dependencies must be
installed. Public functions, classes, arguments, return values, raised
exceptions, and important behaviour should be documented in Python docstrings.

API pages should still contain a short human-written introduction. Generated
signatures explain the interface but do not replace conceptual guidance or
worked examples. See the
[mkdocstrings documentation](https://mkdocstrings.github.io/) before adding
handler-specific options.

## Understand `mkdocs.yaml`

The repository-level `mkdocs.yaml` controls the whole site. Its principal
settings are:

| Setting | Purpose |
| --- | --- |
| `site_name` | Name displayed in the site header; bumpversion updates its version suffix. |
| `site_url` | Canonical deployed URL, including the repository path and trailing slash. |
| `repo_url` | Link from the documentation to the GitHub repository. |
| `docs_dir` | Directory containing documentation sources; currently `docs`. |
| `exclude_docs` | Source files that should not become published pages. |
| `edit_uri` | Controls page-edit links; an empty value hides them. |
| `use_directory_urls` | Produces clean paths such as `/general/dvc/`. |
| `theme` | Selects Material and configures its appearance and features. |
| `plugins` | Enables search and Python API generation. |
| `markdown_extensions` | Enables additional Markdown syntax. |
| `nav` | Defines the order, labels, and hierarchy of pages. |

When adapting the repository as a template, update at least `site_name`,
`site_url`, `repo_url`, copyright, logo, favicon, package references, and
navigation. Retain the version text in `site_name` in the form expected by
`.bumpversion.cfg`.

Do not place passwords, access tokens, private service addresses, or other
secrets in `mkdocs.yaml`; the file is committed to Git and the generated site
may be public.

## Build and validate the site

Before committing documentation, build it with warnings treated as errors:

```bash
uv run mkdocs build --strict
```

MkDocs writes the generated site to `site/`. This directory is disposable
build output: do not edit or commit it. A later build recreates it from the
source documentation.

A useful documentation check is:

```bash
uv sync --locked
uv run --locked mkdocs build --strict
```

The locked form confirms that the committed `uv.lock` can reproduce the
documentation environment without changing dependency resolution.

Review the rendered site as well as the successful build. Automated checks can
find missing files and configuration errors, but not unclear instructions,
incorrect scientific explanations, unreadable diagrams, or commands that do
the wrong thing.

## Documentation workflow

For each documentation change:

1. Update the Markdown, assets, configuration, or Python docstrings.
2. Run `uv run mkdocs serve` and inspect the affected pages locally.
3. Check links, navigation, code blocks, images, and narrow screen layouts.
4. Stop the development server.
5. Run `uv run mkdocs build --strict`.
6. Review `git diff` and confirm that generated `site/` files are not staged.
7. Commit the source changes and open a pull request.

Documentation should normally be reviewed with the code change it describes.
Do not defer documentation until paths, commands, or interfaces have been
forgotten.

## Troubleshooting

### A page is missing from navigation

Confirm that its path is below `docs/` and appears in `nav` using a path
relative to `docs/`. Check YAML indentation carefully.

### A link opens a directory listing

Run `uv run mkdocs serve` and open the URL it prints. Do not browse the built
`site/` directory directly. Also confirm that `site_url` includes the correct
repository path and trailing slash.

### Changes do not appear

Save the Markdown file, check the terminal for a rebuild message, and perform a
normal browser refresh. Restart `mkdocs serve` if the configuration or plugin
environment changed.

### An API page fails to build

Check that the module path is correct and importable in the uv environment:

```bash
uv run python -c "import dermapred"
```

An import-time error in the package can prevent mkdocstrings from collecting
its documentation. Avoid expensive computation, data access, and optional GUI
startup during module import.

### A snippet is empty

Confirm that its source is included in `pymdownx.snippets.base_path`, the named
section markers match, and the include uses the correct filename and section
name. A strict build does not necessarily detect every missing snippet unless
additional snippet path checking is enabled.

## Publishing

Local MkDocs commands do not publish documentation. The repository's GitHub
Actions workflow builds and deploys approved changes from `main`. Follow
[Publishing documentation with GitHub Pages](github-pages.md) for repository
configuration, workflow behaviour, and deployment checks.

## Further reading

- [MkDocs documentation](https://www.mkdocs.org/)
- [MkDocs configuration reference](https://www.mkdocs.org/user-guide/configuration/)
- [Writing documentation with MkDocs](https://www.mkdocs.org/user-guide/writing-your-docs/)
- [Material for MkDocs reference](https://squidfunk.github.io/mkdocs-material/reference/)
- [mkdocstrings documentation](https://mkdocstrings.github.io/)
- [PyMdown Extensions](https://facelessuser.github.io/pymdown-extensions/)
