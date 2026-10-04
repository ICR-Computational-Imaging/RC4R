# Maintenance scripts

This directory contains small, standalone utilities used to maintain the
repository. They support tasks such as preparing documentation assets,
checking repository files, or assisting with a release. They are not part of
the DermaPred application or its research pipeline.

A maintenance script should:

- perform one clearly defined task;
- remain independent of the `dermapred` package where practical;
- accept project-specific paths and settings as command-line arguments;
- explain its inputs, outputs, and usage in its module docstring;
- fail with a clear error and a non-zero exit status;
- avoid silently overwriting source files or other important artifacts;
- never contain credentials, access tokens, or sensitive research data;
- have focused tests under `tests/scripts/`.

Code used to acquire or process research data, train or evaluate models, or
run inference belongs in `src/dermapred/`. Repeatable pipeline stages belong
in `dvc.yaml`. For example, the DermaMNIST downloader is package code under
`src/dermapred/data/`, and its manual acquisition and DVC workflow are covered
in the [data-download guide](../docs/dermapred/data_download.md).

Scripts in this directory are not installed as DermaPred commands. Unless a
script documents a different procedure, run it from the repository root with:

```bash
uv run python scripts/<script_name>.py
```

## Available scripts

### Create a model manifest

`create_model_manifest.py` records model artifact URLs, sizes, and SHA-256 hashes.
It reads the bumpversion-managed `VERSION` file by default and does not upload
anything. See the [model release guide](../docs/dermapred/model_download.md).

### Upload model files to a draft release

`upload_model_release.py` uses the authenticated GitHub CLI (`gh`) to prepare a
draft release and upload the files described by a reviewed manifest:

```bash
uv run python -m scripts.upload_model_release \
  --repo ICR-Computational-Imaging/RC4R \
  --manifest model-release.json \
  --artifact weights=results/trained_models/binary_classifier.pt \
  --artifact calibrator=results/calibration/probability_calibrator.json
```

Run it after pushing the approved release tag. Add `--dry-run` for local checks
without contacting GitHub. The command verifies uploaded attachments, can resume
an incomplete draft, and never overwrites differing assets or publishes a release.
Review and publish the draft separately on GitHub.

### Create a favicon

`create_favicon.py` converts a raster image into a multi-resolution ICO file.
It preserves the source image's aspect ratio, centres it on a transparent
square canvas, and stores several icon sizes in one output file.

Create an ICO containing the default sizes of 16, 32, 48, 64, 128, and 256
pixels:

```bash
uv run python scripts/create_favicon.py input.png favicon.ico
```

Select specific sizes with a comma-separated list:

```bash
uv run python scripts/create_favicon.py \
    --sizes 16,32,48 \
    input.png \
    favicon.ico
```

To recreate this project's documentation favicon:

```bash
uv run python scripts/create_favicon.py \
    --sizes 16,32,48 \
    docs/assets/logo/dermapred-logo-small.png \
    docs/assets/logo/favicon.ico
```

The input must be a raster image supported by Pillow. The output directory
must already exist. SVG input is not supported directly; export the SVG to a
raster format such as PNG before running the script.

Tests for this utility are located in
`tests/scripts/test_create_favicon.py`.
