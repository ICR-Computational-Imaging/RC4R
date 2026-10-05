# Training the binary classifier with DVC

The `train` stage fits the proof-of-concept convolutional network using the
processed training images and binary labels. Validation data are used to
select the checkpoint with the lowest validation loss. The test split remains
untouched for a later evaluation stage.

## Training configuration

Training and augmentation settings are versioned in `params.yaml` under
`training`. DVC records these parameters in `pipelines/training/dvc.lock`, so
changing a value causes the stage to run again.

Current training parameters are:

```yaml
--8<-- "params.yaml:8:17"
```

The stage uses weighted binary cross-entropy with logits. Its positive-class
weight is calculated from the training labels, helping account for the smaller
number of clinically concerning examples. The validation labels do not
influence this weight.

## MONAI augmentation

MONAI applies random horizontal flips, vertical flips, and 90-degree rotations
to training images as they are loaded. These transformations are suitable for
this orientation-independent proof of concept and do not create duplicate
files. Augmentation is never applied to validation images.

The configured random seed is supplied to NumPy, PyTorch, MONAI, and the
training data loader. `num_workers` remains zero by default to keep this
introductory CPU example straightforward and reproducible.

## Run the stage

From the repository root, run:

```bash
uv run --group train dvc repro pipelines/training/dvc.yaml:train
```

DVC runs preprocessing first if its inputs or code have changed. Training
then creates:

```text
results/trained_models/binary_classifier.pt
results/training/history.csv
results/training/loss_curve.png
```

The checkpoint contains the best model state, input-channel count, best epoch,
best validation loss, and training parameters. `history.csv` contains the mean
training and validation loss for every epoch. The PNG is generated from that
CSV by `dermapred.plotting.training`, keeping numerical results separate from
their presentation.

`binary_classifier.pt` and `history.csv` are DVC pipeline outputs.
Do not add them with `dvc add` or commit them directly to Git.
`loss_curve.png` should be added to git to ensure that it is visible in the GitHub repository.
Also, commit `pipelines/training/dvc.yaml`, `pipelines/training/dvc.lock`,
and the generated `.gitignore` files,
then use `dvc push` to upload the artifacts.

After training, continue to
[calibrating the validation probabilities](calibration.md).
