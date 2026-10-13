# RC4R — Reproducible Code for Research

RC4R is a Python project template for reproducible research. It demonstrates
how to connect source code, locked dependencies, versioned data and model
artifacts, automated tests, documentation, and reviewed releases.

**DermaPred** is the worked example: a PyTorch binary classifier using the
public DermaMNIST dataset. Its installable package is named `dermapred` and
provides a small CPU inference API and an image-file command. A user interface
is planned for a later step.

> **Note:** This repository is an educational template. The example model is not intended
  for clinical use or medical decision-making.
>

## What is included

- Python package with image-file inference, automatic resizing, and optional
  probability calibration.
- Model downloader with versioned HTTPS URLs, SHA-256 verification, caching,
  and offline support.
- Separate DVC pipelines for training/validation and held-out test evaluation.
- Synthetic-data tests, including a DVC pipeline integration check.
- GitHub Actions for tests and documentation, plus a manually triggered package-publishing workflow.
- Walkthroughs for Git collaboration, versioning, model releases, and PyPI.

Python **3.11 or newer** is required. Inference needs only PyTorch, NumPy, and
Pillow. Training and evaluation tools are installed separately through uv
dependency groups; inference users do not need DVC or dataset access.

## Get started from the repository

Install Git and [uv](https://docs.astral.sh/uv/getting-started/installation/), then:

```bash
git clone https://github.com/ICR-Computational-Imaging/RC4R.git
cd RC4R
uv sync --locked --no-default-groups
uv run --locked --no-default-groups dermapred --help
```

This creates an inference environment without the development or training
groups. It does not download datasets or model weights.

To work on the template, install the development and training tools instead:

```bash
uv sync --locked --group train
```

## Install the package with pip or uv

To try the package before publication, build a wheel from the repository:

```bash
uv build
```

Install the resulting wheel into your chosen Python environment:

```bash
python -m pip install dist/dermapred-*.whl
```

After a version has been published to PyPI, users can install it without
cloning the repository. Replace `VERSION` with the published version:

```bash
python -m pip install dermapred==VERSION
```

For a project managed with uv:

```bash
uv add dermapred==VERSION
```

Both installers use PyPI by default. See the
[publishing walkthrough](docs/general/publishing_to_pypi.md) for release setup,
TestPyPI and API tokens stored in GitHub environment secrets.

## Run inference on an image

Inference requires either local model files or a trusted model-release
manifest. **No default model manifest is currently included.** Package
installation alone does not provide a trained model.

### Use local model files

From a source checkout with its trained model and matching calibrator:

```bash
uv run --locked --no-default-groups dermapred predict image.jpg \
  --model results/trained_models/binary_classifier.pt \
  --calibrator results/calibration/probability_calibrator.json \
  --image-size 64
```

Replace `image.jpg` with your input image. The example size `64` is for a model
trained on 64-by-64 images. New checkpoints record their trained dimensions,
so `--image-size` can be omitted; legacy checkpoints require it explicitly.
An override must match any dimensions stored in the checkpoint.

For an installed package, use `dermapred predict` directly without the uv
prefix. Omitting `--calibrator` returns raw model probabilities.

### Use a released model bundle

Once a model release and its `model-release.json` are available:

```bash
dermapred predict image.jpg --manifest model-release.json
```

The downloader obtains the matching weights and calibrator, verifies their
checksums, and caches them. Add `--offline` to require verified cached files
without network access. Legacy released checkpoints also need `--image-size`.

### Use the Python API

```python
from dermapred.inference import Predictor

predictor = Predictor.from_manifest("model-release.json")
result = predictor.predict("image.jpg")
print(result.to_dict())
```

Load the predictor once and reuse it. `predict` accepts a filename, a
`pathlib.Path`, or a Pillow image. The result includes the class label,
positive-class probability, raw probability, threshold, and calibration flag.
Class `0` is `benign`; class `1` is `clinically_concerning`.

Images are oriented using EXIF metadata, converted to RGB, resized to the
trained dimensions using bilinear interpolation, and normalised to `[-1, 1]`
with channels first. Direct resizing changes a non-square image's aspect
ratio. See the [inference guide](docs/dermapred/inference.md) for the complete
API, local-file examples, and preprocessing policy.

## Run the tests

```bash
uv run --locked --no-default-groups --group pytest --group train pytest
```

Tests create synthetic data and temporary model files; download and GitHub
upload operations are mocked. They do not require the real datasets, DVC
remotes, or institutional credentials. GitHub Actions runs the suite on Python
3.11 and 3.12 for branch pushes and pull requests.

To check just the final-evaluation pipeline with synthetic data:

```bash
uv run --locked --group pytest --group train \
  pytest tests/dvcstages/test_test_pipeline.py -v
```

This executes the actual test-pipeline YAML in a temporary DVC repository.
It checks pipeline operation, not model performance on held-out data.

## Data and research pipelines

The example downloader acquires public DermaMNIST data separately from DVC
pipeline execution. Training and validation share a development location;
held-out test data have their own location and remote assignment.

| Purpose | Pipeline | Remote |
| --- | --- | --- |
| Training preprocessing, training, and validation-based calibration | `dvc.yaml` | `rds-train` |
| Test-only preprocessing and final evaluation | `pipelines/test/dvc.yaml` | `rds-test` |

The committed remote paths are institutional examples. Configure local mount
paths and obtain the relevant storage permissions before pulling or pushing
data. Remote assignments route artifacts; storage permissions enforce access.
The training pipeline excludes the held-out test split. From the repository
root, `uv run --group train dvc repro` runs training; the test pipeline must be
requested explicitly for final evaluation.

See [data acquisition](docs/dermapred/data_download.md) and
[DVC setup](docs/general/dvc.md) for dataset tracking, local remote overrides,
and targeted pull/push commands. For a new project, adapt the example to your
data policy and keep credentials out of Git.

## Contribute and release

Start with an issue describing the change and its completion criteria. Agree
the scope and target release with a maintainer, create a working branch, run
the relevant checks, and submit a pull request to the agreed destination branch.
Review and merging are separate from publishing a release.

- [Development and release workflow: issues, branches, PRs, and releases](docs/general/development_workflow.md)
- [Publishing the Python package to PyPI](docs/general/publishing_to_pypi.md)
- [Releasing model weights and generating a manifest](docs/dermapred/model_download.md)
- [Code of conduct](CODE_OF_CONDUCT.md)

Use bumpversion to set the approved version before tagging the reviewed release
commit. PyPI distributes the Python package; model files are separate release
assets selected through a manifest. The publishing workflow is in
`.github/workflows/publish.yaml`; configure the GitHub environments and their
API-token secrets before running it manually against a reviewed release tag.

## Documentation and repository layout

Serve the documentation locally:

```bash
uv run --locked --group docs mkdocs serve
```

The terminal displays the local address. To check the documentation build:

```bash
uv run --locked --group docs mkdocs build --strict
```

| Location | Contents |
| --- | --- |
| `src/dermapred/` | Installable package and pipeline stage code |
| `tests/` | Synthetic unit and integration tests |
| `dvc.yaml`, `dvc.lock` | Training pipeline and its recorded state |
| `pipelines/test/` | Separate final-test evaluation pipeline |
| `data/` | Dataset pointers, provenance, and ignored local arrays |
| `results/` | Model artifacts, metrics, and figures |
| `scripts/` | Manifest generation and model-release upload utilities |
| `docs/` | User, contributor, API, and publishing guides |
| `notebooks/` | Exploratory research examples |
| `.github/workflows/` | Enabled GitHub Actions workflows |
| `pyproject.toml` / `uv.lock` | Package requirements and locked development environment |
| `VERSION` | Package version managed by bumpversion |

## Licence

The code is distributed under the [Apache License 2.0](LICENSE). Dataset and
model-artifact licences and attribution requirements must be considered
separately when adapting or distributing the example.
