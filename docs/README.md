# Project documentation

This directory contains the source material for the project's documentation.
Most pages are written in Markdown so that they are readable both in the Git
repository and on the generated documentation website.

MkDocs converts these source files into a static website. The documentation
workflow in `.github/workflows/` can build that website and publish it to
GitHub Pages whenever an approved documentation change is merged.

The documentation has a different purpose from the root `README.md`:

- The root README provides a short introduction and quick start for visitors.
- This directory contains detailed installation, usage, methodology,
  reproducibility, and contribution guidance.
- Python docstrings describe individual modules, classes, and functions and
  can be incorporated into the generated API reference.

A typical documentation process follows this sequence:

```text
Markdown and docstrings -> MkDocs build -> static website -> GitHub Pages
```

Documentation should be updated alongside the code it describes. Commands,
examples, paths, and expected outputs should be tested where practical so that
the published instructions remain reproducible.

GitHub Pages is a public website. Do not include credentials, private URLs,
identifiable research data, or other sensitive information in these files.
