# DVC image preprocessing

The first pipeline stage validates each image array, converts its pixels to
`float32`, scales values from `[0, 255]` to `[-1, 1]`, and changes the array
layout from `(N, H, W, C)` to the `(N, C, H, W)` layout expected by PyTorch.
Run it from the repository root:

```bash
uv run --group train dvc repro pipelines/train/dvc.yaml:preprocess
```

The development pipeline selects `--splits train validation` and creates two
model-ready arrays. It does not require test data:

```text
data/processed_data/train/train_images.npy
data/processed_data/train/validation_images.npy
```

The same preprocessing code can process selected splits from separate input
locations. For a development pipeline, use:

```bash
uv run --group train python -m dermapred.dvcstages.preprocessing \
  --input-dir data/raw_data/train --output-dir data/processed_data/train \
  --splits train validation
```

For a separate evaluation dataset, use its input and output locations with
`--splits test`. Only selected splits are loaded; a missing selected file raises
an error. Omitting `--splits` preserves the default of processing all three.
When changing a DVC stage's selection, update its dependencies and outputs to
match. Final test evaluation is excluded from the training pipeline and belongs
in a separate evaluation pipeline when configured.

The binary labels are unchanged, so the training code will use the label
arrays from `data/raw_data/train` rather than creating duplicate processed copies.

These processed arrays are declared individually under `outs` in
`pipelines/train/dvc.yaml`.
DVC therefore caches and versions them automatically; do not run `dvc add` on
pipeline outputs. Running the preprocessing target again is a no-op unless an
input image, the preprocessing code, or the stage definition has changed.
After reproduction, commit `pipelines/train/dvc.yaml`, its adjacent
`pipelines/train/dvc.lock`, the source code, and the
generated `data/processed_data/train/.gitignore` file to Git. Use `dvc push` to
upload the output data to the configured DVC remote.

## API

::: dermapred.dvcstages.preprocessing
    options:
      show_root_heading: true
      members_order: source
      show_source: true
