# DVC image preprocessing

The first pipeline stage validates each image array, converts its pixels to
`float32`, scales values from `[0, 255]` to `[-1, 1]`, and changes the array
layout from `(N, H, W, C)` to the `(N, C, H, W)` layout expected by PyTorch.
Run it from the repository root:

```bash
uv run --group train dvc repro preprocess
```

The current pipeline explicitly selects all three splits with
`--splits train validation test` and creates three model-ready arrays:

```text
data/processed_data/train_images.npy
data/processed_data/validation_images.npy
data/processed_data/test_images.npy
```

The same preprocessing code can process selected splits from separate input
locations. For a development pipeline, use:

```bash
uv run --group train python -m dermapred.dvcstages.preprocessing \
  --input-dir data/raw_data --output-dir data/processed_data \
  --splits train validation
```

For a separate evaluation dataset, use its input and output locations with
`--splits test`. Only selected splits are loaded; a missing selected file raises
an error. Omitting `--splits` preserves the default of processing all three.
When changing a DVC stage's selection, update its dependencies and outputs to
match. The existing root pipeline still includes final evaluation; splitting
that pipeline and moving data are separate migration steps.

The binary labels are unchanged, so the training code will use the label
arrays from `data/raw_data` rather than creating duplicate processed copies.

These processed arrays are declared individually under `outs` in `dvc.yaml`.
DVC therefore caches and versions them automatically; do not run `dvc add` on
pipeline outputs. Running `dvc repro preprocess` again is a no-op unless an
input image, the preprocessing code, or the stage definition has changed.
After reproduction, commit `dvc.yaml`, `dvc.lock`, the source code, and the
generated `data/processed_data/.gitignore` file to Git. Use `dvc push` to
upload the output data to the configured DVC remote.

## API

::: dermapred.dvcstages.preprocessing
    options:
      show_root_heading: true
      members_order: source
      show_source: true
