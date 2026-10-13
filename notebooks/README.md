# Project notebooks

[Jupyter notebooks](https://jupyter.org/) combine executable code, explanatory
text, equations, tables, and figures in a single document. They are useful for
exploring data, developing ideas, checking assumptions, and communicating an
analysis.

Notebooks complement the Python package in `src/`; they do not replace it.
Reusable data processing, training, evaluation, and inference code should live
in `src/dermapred/` and be imported into notebooks. This keeps important logic
testable and prevents different notebooks from accumulating inconsistent
copies of the same code.

A typical development process is:

```text
Explore in a notebook -> move reusable code into src/ -> add tests -> import it
back into the notebook
```

To keep notebooks reproducible:

- Run cells from top to bottom without relying on hidden interactive state.
- Restart the kernel and run all cells before considering an analysis complete.
- Use project-relative paths rather than paths tied to one person's computer.
- Load datasets from the root `data/` directory and manage them with DVC.
- Record important parameters rather than changing unexplained values between
  cells.
- Avoid committing large generated outputs unless they are needed to
  understand the analysis.

Notebook files and their Markdown content may be committed to Git, but data,
model artifacts, credentials, and sensitive research information must not be
embedded in them. In particular, inspect saved cell outputs before committing a
notebook.

## Notebooks in this repository

The sections below describe the purpose, inputs, outputs, and expected execution
order of each notebook or group of notebooks in this project.
