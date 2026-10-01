# DVC image preprocessing

The first pipeline stage validates each image array, converts its pixels to
`float32`, scales values from `[0, 255]` to `[-1, 1]`, and changes the array
layout from `(N, H, W, C)` to the `(N, C, H, W)` layout expected by PyTorch.
Run it from the repository root:

```bash
uv run --group train dvc repro preprocess
```

The stage creates three model-ready arrays:

```text
data/processed_data/train_images.npy
data/processed_data/validation_images.npy
data/processed_data/test_images.npy
```

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
