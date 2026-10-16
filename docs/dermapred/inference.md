# Installing and running image inference

The pip package provides an image-inference API and a `dermapred predict`
command. Its runtime dependencies are PyTorch, NumPy, Pillow, PyQt6, and
Matplotlib. DVC, MONAI, scikit-learn, and dataset download tools are development
dependencies.

The included [desktop interface](ui.md) uses PyQt6 and Matplotlib for selecting
an image region and running calibrated inference. It is available with the
standard installation.

This is an educational template. The example model is not intended for
clinical use or medical decision-making.

## Install the package

Before publication, build the package from the repository root:

```bash
uv build
```

Install the resulting wheel into the environment where you want to run inference:

```bash
python -m pip install dist/dermapred-*.whl
```

After the maintainer has published the chosen version to PyPI, users can install
that version without cloning the repository:

```bash
python -m pip install dermapred==VERSION
```

Replace `VERSION` with the published version. This page does not claim the
package or its model artifacts have already been published.

The Python wheel contains the code; model weights and their matching calibrator
are distributed separately using the [model release workflow](model_download.md).
Installing the package does not download a dataset or model. The desktop UI and
`Predictor.from_release()` can retrieve `model-release.json` from the public
GitHub Release matching the installed package version. The command-line
`dermapred predict` examples below still accept a trusted local manifest or
explicit model files.

## Try the bundled example image

The example image is bundled inside the installed Python package, so users
do not need to locate an installation folder, clone the repository, or
download a dataset to try an image. Model weights and the calibrator are still
obtained separately through the release downloader or local model files.

### Use the Python API

Use `importlib.resources` to read the image regardless of where the package is
installed or which directory you run Python from:

```python
from importlib.resources import files

from PIL import Image

from dermapred.inference import Predictor

example = files("dermapred").joinpath("examples", "example_image.jpg")
with example.open("rb") as stream:
    with Image.open(stream) as opened:
        image = opened.convert("RGB")

predictor = Predictor.from_release()
result = predictor.predict(image)
print(result.to_dict())
```

This reads the entire example image without selecting a region. It uses the
published model release matching the installed package version. For a
development checkout without a matching public release, use
`Predictor.from_release(version="YOUR_PUBLISHED_VERSION")` or the local-model
constructor described below.

### Use the desktop interface

After installing the package, launch the UI:

```bash
python -m dermapred.ui
```

Click **Load example**, draw the red bounding box around the mole, and click
**Infer**. The button loads the bundled image directly and clears any previous
selection and result. No file browsing or image download is required. From a
repository checkout, launch with `uv run --locked python -m dermapred.ui`. See the
[desktop guide](ui.md) for model selection and the square-cropping behaviour.

### Use the image-file command

To use the example with the image-file CLI, copy the bundled image into your
current directory. This copy is not needed for the UI. Run this in your Python environment:

```python
from importlib.resources import files
from pathlib import Path

example = files("dermapred").joinpath("examples", "example_image.jpg")
destination = Path("example_image.jpg")
with destination.open("xb") as output:
    output.write(example.read_bytes())
print(destination.resolve())
```

This prints the copied file's location and refuses to overwrite an existing
`example_image.jpg`. Use the copy with the image-file command:

```bash
dermapred predict example_image.jpg --manifest model-release.json
```

The command above requires a local release manifest; automatic manifest
selection is available through the desktop UI and `Predictor.from_release()`.

## Run inference with local model files

Use the checkpoint and calibrator from the same verified model release:

```bash
dermapred predict image.jpg \
  --model binary_classifier.pt \
  --calibrator probability_calibrator.json
```

New checkpoints record their training image dimensions, so inference selects
the input size automatically. Older checkpoints lack that information. For
those, add the size used during training, for example `--image-size 64` for
a model trained with 64-by-64 images. Do not guess the size from the filename
or use the dimensions of the image being submitted.

Omitting `--calibrator` produces raw model probabilities. The JSON result
includes `calibrated: false` to identify this mode. For release-model inference,
use its matching calibrator.

The command prints JSON containing the predicted label, binary class index,
positive-class probability, raw probability, threshold, and calibration flag.
Class `0` means `benign`; class `1` means `clinically_concerning`. The threshold
defaults to `0.5`. Use `--threshold` only to supply the threshold agreed for that
model; changing it changes the predicted class.

## Run inference from a model manifest

```bash
dermapred predict image.jpg --manifest model-release.json
```

The package downloads the manifest's weights and calibrator from their pinned
HTTPS URLs. It verifies byte counts and SHA-256 checksums before loading them,
and caches them for subsequent runs. The manifest must contain both `weights`
and `calibrator` roles. Add `--image-size` for legacy checkpoints as above.

After downloading the bundle once, require inference without network access:

```bash
dermapred predict image.jpg --manifest model-release.json --offline
```

An absent or corrupt cached artifact causes an explicit error in offline mode.
`--cache-dir PATH` selects a cache location; `DERMAPRED_CACHE_DIR` also overrides
the platform default. Only load checkpoints and manifests from trusted sources.

## Use the Python API

```python
from dermapred.inference import Predictor

predictor = Predictor.from_release()
result = predictor.predict("image.jpg")
print(result.label)
print(result.probability)
print(result.to_dict())
```

`from_release()` downloads and caches the public manifest for the installed
version, then verifies and loads its weights and calibrator. The matching tag
must have a published release with a `model-release.json` asset. It does not
fall back to `latest`. Pass `version="0.1.1"` to explicitly select a published
model during development, or `offline=True` to require a cached bundle. A local
manifest can still be loaded with `Predictor.from_manifest("model-release.json")`.

For local artifacts:

```python
from dermapred.inference import Predictor

predictor = Predictor(
    "binary_classifier.pt",
    calibrator_path="probability_calibrator.json",
    # For legacy checkpoints only: image_size=64,
)
result = predictor.predict("image.jpg")
```

Load the predictor once and reuse it for subsequent images. `predict` accepts
an image path or a Pillow `Image.Image`, allowing the desktop interface to
call the same API without duplicating inference logic. Inference currently
runs on the CPU and returns one prediction per call.

## How input images are prepared

The API performs these steps before calling the model:

1. Apply the image's EXIF orientation.
2. Convert to RGB, including grayscale or RGBA inputs.
3. Resize directly to the checkpoint's trained height and width using bilinear
   interpolation. Images already at the correct size are not resampled.
4. Apply the existing training preprocessing: scale pixels from `[0, 255]` to
   `[-1, 1]`, convert to `float32`, and arrange channels first.
5. Run the model in evaluation mode with gradient calculation disabled, then
   apply the matching probability calibrator if supplied.

Direct resizing changes the aspect ratio of non-square images. No cropping or
padding is currently applied. For the template, this is an explicit input
policy; adaptations should choose and verify their preprocessing policy using
development data before final evaluation. Resizing alone does not make
arbitrary photographs equivalent to the model's training distribution.

Future training runs save `image_size` in their checkpoint. This metadata does
not modify existing checkpoints; they require an explicit size. The inference
API rejects overrides that disagree with stored training dimensions.

## API reference

::: dermapred.inference.predictor.Predictor

::: dermapred.inference.predictor.Prediction
