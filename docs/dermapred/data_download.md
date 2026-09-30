# Downloading and tracking the example data

This tutorial downloads the DermaMNIST data used by the DermaPred example and
then places it under DVC control. The download is intentionally performed
separately from the DVC pipeline so that new DVC users can practise the common
workflow for data obtained from a collaborator, instrument, shared drive, or
external repository.

The two operations have different purposes:

- The Python command obtains the data and writes ordinary files to the
  workspace.
- `dvc add` versions those files by content and creates small pointer files
  that can be committed to Git.

## Prerequisites

Run all commands from the repository root. Before starting:

1. [Set up DVC](../general/dvc.md), including a suitable remote.
2. Confirm that you are permitted to store the dataset in that remote.
3. Install the dependencies used for data acquisition:

```bash
uv sync --group train
```

## 1. Download the data

The following command downloads the default 64 × 64 version:

```bash
uv run --group train python -m dermapred.data.download_data data/raw_data
```

The downloader supports image sizes `28`, `64`, `128`, and `224`. Select a
different size with `--size`:

```bash
uv run --group train python -m dermapred.data.download_data \
    data/raw_data --size 128
```

The command creates six NumPy arrays and a provenance YAML file:

```text
data/raw_data/dataset.yaml
data/raw_data/train_images.npy
data/raw_data/train_labels.npy
data/raw_data/validation_images.npy
data/raw_data/validation_labels.npy
data/raw_data/test_images.npy
data/raw_data/test_labels.npy
```

`dataset.yaml` records the dataset name, selected image size, installed
MedMNIST version, and source URL. The downloader generates it automatically so
the provenance can be committed to Git alongside the DVC pointers. It is not
added to DVC.

Inspect the files before tracking them. In a real research project, this is
also the point at which you should confirm provenance, licensing, consent,
information-governance requirements, and the absence of unexpected sensitive
information.

## 2. Add the data to DVC

Track each NumPy array as an individual DVC target:

```bash
uv run --group train dvc add data/raw_data/*.npy
```

DVC now:

- calculates a checksum for each array;
- stores each array in the local DVC cache;
- creates a corresponding pointer such as
  `data/raw_data/train_images.npy.dvc` for every array;
- adds the `.npy` filenames to `data/raw_data/.gitignore` so the arrays are
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

## 3. Review and stage the metadata

Check what changed:

```bash
git status
uv run --group train dvc status
```

Stage the DVC pointers, generated Git ignore rule, and provenance file:

```bash
git add \
    data/raw_data/*.dvc \
    data/raw_data/.gitignore \
    data/raw_data/dataset.yaml
```

Do not add the `.npy` files to Git, because the arrays themselves belong in
DVC. `dataset.yaml` is deliberately tracked by Git because it is small,
human-readable provenance rather than dataset content.

## 4. Upload and commit the data version

Upload any content that is not already present in the configured DVC remote:

```bash
uv run --group train dvc push
```

Then commit the metadata to Git:

```bash
git commit -m "Track 64x64 DermaMNIST data"
git push
```

Git now records the code, provenance, and six `.dvc` pointers. The DVC remote
stores the corresponding arrays. Together, they allow another authorised user
to restore this version with:

```bash
git pull
uv run --group train dvc pull
```

## Updating the dataset

For example, replace the tracked 64 × 64 data with the 128 × 128 version and
then add the arrays again:

```bash
uv run --group train python -m dermapred.data.download_data \
    data/raw_data --size 128
uv run --group train dvc add data/raw_data/*.npy
uv run --group train dvc push
```

The existing `.npy.dvc` files are updated rather than duplicated. If an array
has not changed, its pointer and cached content remain unchanged. The
downloader also updates the Git-tracked `dataset.yaml`. Stage and commit these
changes together:

```bash
git add data/raw_data/*.dvc data/raw_data/dataset.yaml
git commit -m "Use 128x128 DermaMNIST data"
git push
```

DVC identifies content by checksum. If this exact dataset was uploaded
previously, `dvc push` recognises it and does not upload another copy.
Individual pointers can also be pushed separately when required; for example:

```bash
uv run --group train dvc push data/raw_data/train_images.npy.dvc
```

> **Note:** "When is `dvc unprotect` needed?"
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
