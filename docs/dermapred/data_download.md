# Downloading and tracking the example data

This tutorial downloads the DermaMNIST data used by the DermaPred example and
then places it under DVC control. The download is intentionally performed
separately from the DVC pipeline so that new DVC users can practise the common
workflow for data obtained from a collaborator, instrument, shared drive, or
external repository.

The two operations have different purposes:

- The Python command obtains the data and writes ordinary files to the
  workspace.
- `dvc add` versions those files by content and creates a small metadata file
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

The command creates six NumPy arrays:

```text
data/raw_data/train_images.npy
data/raw_data/train_labels.npy
data/raw_data/validation_images.npy
data/raw_data/validation_labels.npy
data/raw_data/test_images.npy
data/raw_data/test_labels.npy
```

Inspect the files before tracking them. In a real research project, this is
also the point at which you should confirm provenance, licensing, consent,
information-governance requirements, and the absence of unexpected sensitive
information.

## 2. Add the data to DVC

Track the directory as one dataset:

```bash
uv run --group train dvc add data/raw_data
```

DVC now:

- calculates checksums for the directory and its contents;
- stores the content in the local DVC cache;
- creates `data/raw_data.dvc`, which identifies this exact dataset version;
- adds `/raw_data` to `data/.gitignore` so the arrays are not committed to
  Git.

The generated `raw_data.dvc` file is small and should be committed to Git. The
`.npy` files should not be added to Git.

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

Stage the DVC pointer and generated Git ignore rule:

```bash
git add data/raw_data.dvc data/.gitignore
```

Do not use `git add data/raw_data`, because the data themselves belong in DVC.

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

Git now records the code and the `raw_data.dvc` pointer. The DVC remote stores
the corresponding arrays. Together, they allow another authorised user to
restore this version with:

```bash
git pull
uv run --group train dvc pull
```

## Updating the dataset

For example, replace the tracked 64 × 64 data with the 128 × 128 version and
then add the directory again:

```bash
uv run --group train python -m dermapred.data.download_data \
    data/raw_data --size 128
uv run --group train dvc add data/raw_data
uv run --group train dvc push
```

The existing `data/raw_data.dvc` file is updated rather than duplicated. Stage
and commit that change:

```bash
git add data/raw_data.dvc
git commit -m "Use 128x128 DermaMNIST data"
git push
```

DVC identifies content by checksum. If this exact dataset was uploaded
previously, `dvc push` recognises it and does not upload another copy.

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
