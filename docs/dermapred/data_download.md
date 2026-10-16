# Downloading and tracking the example data

This tutorial downloads the DermaMNIST data used by the DermaPred example and
then places it under DVC control. The download is intentionally performed
separately from the DVC pipeline so that new DVC users can practise the common
workflow for data obtained from a collaborator, instrument, shared drive, or
external repository.

This downloader obtains the public, openly available DermaMNIST example data,
including every split. Separate folders organize the example; they do not
restrict who can download it. Real projects should obtain restricted training
and held-out test data through institution-approved access controls, such as
network folders with permissions granted separately to contributors and
authorized evaluators.

The two operations have different purposes:

- The Python command obtains the data and writes ordinary files to the
  workspace.
- `dvc add` versions those files by content and creates small pointer files
  that can be committed to Git.

## Prerequisites

Run all commands from the repository root. Before starting:

1. [Set up DVC](../general/dvc.md), including remotes named `rds-train` and
   `rds-test`. Training and validation use `rds-train`; test data use `rds-test`.
2. Confirm that you are permitted to store the dataset in each remote you use.
   A network or storage administrator controls access to the underlying folders.
3. Install the dependencies used for data acquisition:

```bash
uv sync --group train
```

Check the configured locations with `uv run --group train dvc remote list`.
Shared locations belong in `.dvc/config`; machine-specific mount paths can be
overridden in `.dvc/config.local` with `dvc remote modify --local NAME url PATH`.
The remote names stay the same on each machine.

## 1. Download the data

The selected image size is stored in the Git-tracked `params.yaml` file:

```yaml
--8<-- "params.yaml:4:6"
```

The value may be `28`, `64`, `128`, or `224`. Keeping this acquisition choice
in `params.yaml` makes it explicit and reproducible; downloading remains a
manual operation rather than a DVC pipeline stage.

The following command reads `params.yaml` and downloads the configured data
version:

```bash
uv run --group train python -m dermapred.data.download_data data/raw_data
```

The command creates six NumPy arrays and a provenance YAML file in each folder:

```text
data/raw_data/train/dataset.yaml
data/raw_data/train/train_images.npy
data/raw_data/train/train_labels.npy
data/raw_data/train/validation_images.npy
data/raw_data/train/validation_labels.npy
data/raw_data/test/dataset.yaml
data/raw_data/test/test_images.npy
data/raw_data/test/test_labels.npy
```

The downloader replaces files with the same names. These are local workspace
folders; the DVC remotes are separate storage locations managed by DVC.

### Binary classification labels

For this introductory example, the downloader converts DermaMNIST's original
seven-class labels and saves the result in each `*_labels.npy` file:

| Binary label | Meaning | Original DermaMNIST diagnoses |
| ---: | --- | --- |
| `0` | Benign | Benign keratosis-like lesions; dermatofibroma; melanocytic nevi; vascular lesions |
| `1` | Clinically concerning | Actinic keratoses and intraepithelial carcinoma; basal cell carcinoma; melanoma |

The positive class contains actinic keratoses and intraepithelial carcinoma,
basal cell carcinoma, and melanoma. It is called **clinically concerning**,
not simply malignant, because the first category combines premalignant
actinic keratoses with intraepithelial carcinoma.

The downloaded seven-class labels are not saved separately in this example.
They remain available from the original MedMNIST source and can be retained in
a future multiclass experiment by changing the downloader.

### `dataset.yaml`

`dataset.yaml` records the dataset name, selected image size, installed
MedMNIST version, and source URL. The downloader generates it automatically so
the provenance can be committed to Git alongside the DVC pointers. It also
explicitly records that the saved labels are binary and gives
the meaning of values `0` and `1`. Both folders receive this provenance record.

Inspect the files before tracking them via `git status`. In a real research project, this is
also the point at which you should confirm provenance, licensing, consent,
information-governance requirements, and the absence of unexpected sensitive
information.

## 2. Add the data to DVC

Track each NumPy array as an individual DVC target:

```bash
uv run --group train dvc add data/raw_data/train/*.npy
uv run --group train dvc add data/raw_data/test/*.npy
```

DVC now:

- calculates a checksum for each array;
- stores each array in the local DVC cache;
- creates a corresponding pointer such as
  `data/raw_data/train/train_images.npy.dvc` for every array;
- adds the `.npy` filenames to the `.gitignore` in each dataset folder so the arrays are
  not committed to Git.

The generated `.dvc` files are small and should be committed to Git. The
`.npy` files should not be added to Git. Tracking the arrays separately also
lets users address or transfer one DVC target at a time when working with a
large dataset.

By default, DVC restores workspace data using a **reflink** when the file
system supports it, otherwise it creates an independent **copy**. Both methods
allow the workspace files to be modified safely without changing the version
already stored in the DVC cache. A reflink uses copy-on-write, so unchanged
disk blocks can initially be shared while the files still behave like
independent copies.

> **Note:**
> `dvc add` records data in the local cache. It does not upload the data to
> the configured remote; that happens when `dvc push` is run.

Before staging or uploading, record the intended remote under each pointer's
`outs` entry: `remote: rds-train` for training/validation arrays and
`remote: rds-test` for test arrays. The downloader and ordinary `dvc add` do not
assign these for you. Preserve all generated fields and add the remote beside
them, for example:

```yaml
outs:
- md5: ...        # Keep the generated value
  size: ...       # Keep the generated value
  hash: md5
  path: test_images.npy
  remote: rds-test
```

These assignments are committed with the dataset version and control future
transfers. Files without assignments fall back to the default remote, so check
that all six pointers have the appropriate field.

## 3. Review and stage the metadata

Check what changed:

```bash
git status
uv run --group train dvc status
```

Stage the training and validation pointers, ignore rules, and provenance:

```bash
git add \
    data/raw_data/train/*.dvc \
    data/raw_data/train/.gitignore \
    data/raw_data/train/dataset.yaml
```

Test metadata are staged separately:

```bash
git add \
    data/raw_data/test/*.dvc \
    data/raw_data/test/.gitignore \
    data/raw_data/test/dataset.yaml
```

Stage `params.yaml` too if you deliberately changed the configured image size.
Run `git diff --staged` before committing. For separate training and test commits,
stage only one group, complete its upload and commit, then repeat for the other.

Do not add the `.npy` files to Git, because the arrays themselves belong in
DVC. `dataset.yaml` is deliberately tracked by Git because it is small,
human-readable provenance rather than dataset content.

## 4. Upload and commit the data version

Upload each group to its saved remote. No `-r` is needed; the targets limit
what is uploaded:

```bash
uv run --group train dvc push data/raw_data/train/*.npy.dvc
uv run --group train dvc push data/raw_data/test/*.npy.dvc
```

After the applicable uploads succeed, commit the staged metadata to Git using
an appropriate commit message, for example:

```bash
git commit -m "Track 28x28 DermaMNIST data"
git push
```

Git records provenance and `.dvc` pointers; the two DVC remotes store their
respective arrays. Push your issue branch and submit a PR following
[the collaboration walkthrough](../development_workflow.md).

## 5. Pull an existing dataset

After cloning the repository, or updating your local branch, the committed
`.dvc` files must be present. You do not need to rerun the downloader or
`dvc add` to retrieve an existing version.

Contributors with development-data access can retrieve training and validation:

```bash
uv run --group train dvc pull data/raw_data/train/*.npy.dvc
```

Authorized evaluators can retrieve test arrays separately:

```bash
uv run --group train dvc pull data/raw_data/test/*.npy.dvc
```

These commands retrieve raw arrays only. They do not download processed data or
model outputs. The `dataset.yaml` files come from Git. A missing mount or
insufficient storage permissions prevents downloading the corresponding data.

### Why pulls are targeted

Saved remote assignments prevent an accidental `dvc push` from sending test
arrays to the training default. They do not grant access to storage. A blanket
`dvc pull` can fail if test data need downloading and the person lacks access
to the test remote. Targeting development data excludes test files altogether.
An explicit `-r` option selects a remote; it does not filter datasets, and saved
per-output assignments take precedence over that option.

## 6. Reproduce and transfer pipeline outputs

The training pipeline is in the root `dvc.yaml`. Final evaluation stays in
`pipelines/test/dvc.yaml` and is requested separately to keep held-out testing
out of routine training. When training inputs, dependencies, parameters, or
pipeline definitions change, run:

```bash
uv run --group train dvc repro
```

DVC runs stages as needed and updates `dvc.lock`. Unchanged
stages are skipped; changing remote assignments alone does not require
recomputing outputs. Review the lockfile and commit it with the pipeline YAML.

Each cached data, model, plot, and report output in the training pipeline
records `remote: rds-train`. Documentation copies use `cache: false` and are
stored in Git instead:

```yaml
outs:
- results/trained_models/binary_classifier.pt:
    remote: rds-train
```

The training pipeline's outputs include processed training and validation
images, model weights, training history, and the calibrator. They are already
DVC-managed; do not run `dvc add` on them. Upload all of them by targeting the
pipeline file:

```bash
uv run --group train dvc push dvc.yaml
```

An authorized person with write access to both remotes can upload the raw
arrays and pipeline outputs together:

```bash
uv run --group train dvc push \
    data/raw_data/train/*.npy.dvc data/raw_data/test/*.npy.dvc \
    dvc.yaml
```

To retrieve the pipeline outputs, use:

```bash
uv run --group train dvc pull dvc.yaml
```

To retrieve raw development data and all training pipeline outputs together:

```bash
uv run --group train dvc pull \
    data/raw_data/train/*.npy.dvc dvc.yaml
```

These targets exclude test data. New outputs declared in the training pipeline
are included automatically. DVC transfers cached output content; the pipeline
YAML, lockfile, documentation copies of plots and metrics, and provenance are Git-tracked and
shared with `git push`.

## Updating the dataset

For example, to replace the tracked 28 × 28 data with the 128 × 128 version,
first change `data.dermamnist.image_size` in `params.yaml` to `128`. Then run
the downloader without a command-line override and add the arrays again:

```bash
uv run --group train python -m dermapred.data.download_data data/raw_data
uv run --group train dvc add data/raw_data/train/*.npy
uv run --group train dvc add data/raw_data/test/*.npy
uv run --group train dvc push data/raw_data/train/*.npy.dvc
uv run --group train dvc push data/raw_data/test/*.npy.dvc
```

The existing `.npy.dvc` files are updated rather than duplicated. Before
uploading, verify that they still record the correct remote assignments. If an array
has not changed, its pointer and cached content remain unchanged. The
downloader also updates both Git-tracked `dataset.yaml` files. Stage and commit these
changes together:

```bash
git add params.yaml \
    data/raw_data/train/*.dvc data/raw_data/train/dataset.yaml \
    data/raw_data/test/*.dvc data/raw_data/test/dataset.yaml
git commit -m "Use 128x128 DermaMNIST data"  # Make sure the message is appropriate!
git push
```

DVC identifies content by checksum. If this exact dataset was uploaded
previously, `dvc push` recognises it and does not upload another copy.
Individual pointers can also be pushed separately when required; for example:

```bash
uv run --group train dvc push data/raw_data/train/train_images.npy.dvc
```

> **Note:** "When is `dvc unprotect` needed?"
> `dvc unprotect` makes DVC-managed files writable so that they can be replaced or
> updated without changing the protected copy stored in DVC’s cache.
> `dvc unprotect` is not normally required. DVC avoids hard links and
> symbolic links by default, using the safe `reflink,copy` strategy instead.
> If an advanced cache configuration explicitly uses `hardlink` or
> `symlink`, the workspace files may be read-only to protect the cache. In
> that case, run the following before modifying them:
>
> ```bash
>    uv run --group train dvc unprotect data/raw_data
> ```
>
> See DVC's documentation on
> [cache link types](https://dvc.org/doc/user-guide/data-management/large-dataset-optimization)
> for the performance, storage, and editing trade-offs.
