# Desktop image inference

The optional PyQt6 interface displays images using an embedded Matplotlib
canvas. Select a mole with a red bounding box, then run the existing calibrated
inference engine on that region. This is an educational example and is not
intended for clinical use or medical decisions.

## Install and launch

Install the optional desktop dependencies with pip or uv:

```bash
python -m pip install 'dermapred[ui]'
```

From a repository checkout:

```bash
uv sync --locked --extra ui
uv run --locked --extra ui python -m dermapred.ui --manifest model-release.json
```

For an installed package, use:

```bash
python -m dermapred.ui --manifest model-release.json
```

Supply a trusted local [release manifest](model_download.md). The weights and
matching calibrator are downloaded and verified when you first click **Infer**,
then cached for subsequent use. `--offline` requires verified cached artifacts;
`--cache-dir PATH` selects the cache location. The UI does not retrieve the
manifest itself and does not download anything merely on launch.

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

1. Click **Open image** and choose a JPEG, TIFF, PNG, or BMP file. TIFF files
   use their first frame. EXIF orientation is applied before display.
2. On the left-hand image panel, hold the left mouse button and drag around
   the suspect mole. The red box updates while you drag. Release to finish.
3. Drawing another box replaces the old selection and clears the old result.
   Opening another image also clears both.
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

Tests use synthetic images, offscreen Qt, and mocked model loading and inference.
They do not require trained weights, private datasets, or network access.

```bash
QT_QPA_PLATFORM=offscreen uv run --locked --extra ui --group train \
  pytest tests/ui --cov-reset --cov=dermapred.ui --cov-fail-under=80
```

The unit-test workflow installs the UI extra, runs these tests on Linux with
Python 3.11 and 3.12, and enforces at least 80% coverage of the UI package.
Before release, also check the interface interactively on each desktop platform
you intend to support; automated offscreen tests do not verify native dialogs,
desktop packaging, or visual appearance on those platforms.
