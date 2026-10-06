# Calibrating model probabilities with DVC

The `calibrate` stage converts the classifier's soft outputs into probabilities
that better represent the observed frequency of clinically concerning lesions.
It uses only validation images and labels; the test split remains untouched for
the later evaluation stage.

## Choose a method

The method is selected in `params.yaml`:

```yaml
--8<-- "params.yaml:19:24"
```

Supported methods are:

- `isotonic`: learns a flexible monotonic mapping from raw probabilities to
  calibrated probabilities. It makes few shape assumptions but can overfit
  when calibration data are limited.
- `platt`: fits a logistic mapping to the model logits. It is less flexible
  but is often more stable with smaller calibration datasets.

Changing `calibration.method` reruns calibration without retraining the neural
network.

## Cross-validated validation evidence

Fitting and assessing a calibrator on the same samples would make the apparent
improvement optimistic. The stage therefore uses stratified cross-validation
to produce the **after-calibration** validation probabilities: each validation
sample is calibrated by a mapping fitted without that sample.

After producing this out-of-fold evidence, the stage fits one final calibrator
on the complete validation set. That final mapping is stored for application
to the untouched test predictions.

## Run the stage

From the repository root, run calibration and any required upstream stages with:

```bash
uv run --group train dvc repro pipelines/train/dvc.yaml:calibrate
```

The stage creates:

```text
results/calibration/probability_calibrator.json
results/calibration/validation_metrics.json
results/calibration/validation_calibration.png
```

`probability_calibrator.json` is a DVC-managed output containing either the
isotonic thresholds or the Platt coefficient and intercept. JSON keeps the
mapping transparent and avoids loading a Python pickle during evaluation.

The metrics and PNG are small review artifacts tracked directly by Git. The
metrics report Brier score and expected calibration error before and after
out-of-fold calibration. The reliability diagram compares both probability
curves with perfect calibration, making the current model behaviour visible on
GitHub.

Because the Git-tracked review files are not DVC outputs, deleting only one of
them does not make DVC consider the stage incomplete. A calibration run always
regenerates both files.

After calibration, continue to the
[final evaluation on the untouched test set](evaluation.md).
