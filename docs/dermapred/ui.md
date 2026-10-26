# Desktop image inference

The included PyQt6 interface displays images using an embedded Matplotlib
canvas. Select a mole with a red bounding box, then run the existing calibrated
inference engine on that region. This is an educational example and is not
intended for clinical use or medical decisions.

## Install and launch

The desktop dependencies are included in the standard package installation:

```bash
python -m pip install dermapred
```

From a repository checkout:

```bash
uv sync --locked
uv run --locked python -m dermapred.ui
```

For an installed package, use:

```bash
python -m dermapred.ui
```

No local manifest is needed by default. The UI uses the **installed package
version**, without requiring a Git checkout. For version `0.1.1`, it retrieves:

```text
https://github.com/ICR-Computational-Imaging/RC4R/releases/download/v0.1.1/model-release.json
```

The manifest, weights, and matching calibrator are fetched when you first click
**Infer**, then cached for subsequent use. The manifest must match the requested
version and point to assets in that same public release; weights and calibrator
are verified against its byte counts and SHA-256 hashes. Nothing is downloaded
merely on launch or installation. `--offline` requires a valid cached manifest
and verified cached artifacts; `--cache-dir PATH` selects their cache location.

The release must be published, with an asset named **`model-release.json`**.
Draft releases cannot be downloaded anonymously. There is no automatic fallback
to another version or the latest release. Development versions usually do not
have a public release yet: use local model files, or explicitly select a
published version while developing:

```bash
uv run --locked python -m dermapred.ui --release-version 0.1.1
```

Replace `0.1.1` with an actual published model release. `--repo OWNER/REPOSITORY`
selects another project's public release location when adapting this template.

You can still supply a trusted local [release manifest](model_download.md):

```bash
python -m dermapred.ui --manifest model-release.json
```

Alternatively, supply both local model files:

```bash
python -m dermapred.ui \
  --model binary_classifier.pt \
  --calibrator probability_calibrator.json
```

Both sources require a calibrator; the interface always reports calibrated
probabilities. Input dimensions come from checkpoint metadata. For older
checkpoints, supply the known training size with `--image-size 64`, for example.
The application does not read a repository-local `params.yaml`: installed
packages use the loaded model's requirements. An explicit size that conflicts
with checkpoint metadata is rejected by the inference engine.

## Select an image and run inference

1. Click **Load example** to display the bundled example immediately, or click
   **Open image** to choose your own JPEG, TIFF, PNG, or BMP file. The example
   works after pip installation without locating package files or downloading
   an image. TIFF files use their first frame. EXIF orientation is applied before display.
2. On the left-hand image panel, hold the left mouse button and drag around
   the suspect mole. The red box updates while you drag. Release to finish.
3. Drawing another box replaces the old selection and clears the old result.
   Opening another image or clicking **Load example** also clears both.
4. Click **Infer**. A missing or zero-area selection produces an explanatory
   dialog instead of a prediction.
5. Read the calibrated probability of `clinically_concerning` in the results
   panel on the right. The predicted class uses the existing default threshold
   of `0.5`; the displayed probability always refers to the positive class.

The selected pixels are taken from the original-resolution image, with the box
clipped to image boundaries. The longer dimension is centre-cropped to make a
square. The existing Predictor then resizes to its training dimensions and
reuses `dermapred.data.preprocessing` for scaling and channel conversion.
This square-crop policy belongs to the UI; direct API inference continues to
accept uncropped images.

Image loading, model downloading, and inference run in background threads.
Selection and inference controls are disabled while an operation is in
progress. Failures open a dialog and allow another attempt. **Cancel** closes
the workspace without starting inference. If an operation is already running,
the window hides immediately and the process exits once the operation finishes;
it does not forcibly interrupt a download or a model operation.

## Tests

Tests use synthetic images, the bundled example, offscreen Qt, and mocked model loading and inference.
They do not require trained weights, private datasets, or network access.

```bash
QT_QPA_PLATFORM=offscreen uv run --locked --group train \
  pytest tests/ui --cov-reset --cov=dermapred.ui --cov-fail-under=80
```

The unit-test workflow runs these tests on Linux with
Python 3.12, and enforces at least 80% coverage of the UI package.
Before release, also check the interface interactively on each desktop platform
you intend to support; automated offscreen tests do not verify native dialogs,
desktop packaging, or visual appearance on those platforms.
