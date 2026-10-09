# Evaluating a selected model on the test set

Final test evaluation is separate from the training pipeline in the root
`dvc.yaml`. Test preprocessing and evaluation are defined in
`pipelines/test/dvc.yaml` so using the held-out data is an explicit step,
separate from routine training.

## Run the evaluation pipeline

Run it explicitly from the repository root:

```bash
uv run --group train dvc repro pipelines/test/dvc.yaml
```

DVC generates `pipelines/test/dvc.lock` beside the pipeline YAML. Each stage
uses `wdir: ../..` so its paths are relative to the repository root. See
[the pipeline layout](../../general/dvc.md#pipeline-locations-in-this-repository).

The preprocessing stage reads `data/raw_data/test/` and processes only the
`test` split into `data/processed_data/test/`. Raw and processed test data and
sample predictions are assigned to `rds-test`. The network or storage
administrator controls who can access it. Missing required test data causes
evaluation to fail.

Evaluate the selected, fixed classifier and validation-fitted calibrator.
Evaluation must not fit a model, choose a checkpoint, tune a threshold, or alter
the calibrator. Record the model and calibrator hashes, code commit, dataset
version, configuration, and results together. Selecting a DVC pipeline can also
reproduce changed upstream stages; preserve the candidate and verify that the
weights evaluated are the weights intended for release.

## Keep the held-out test set separate

Use training data to fit models and validation data to compare architectures,
preprocessing, augmentation, hyperparameters, and thresholds. Calibration is
fitted using validation data too. Use the held-out test set at agreed final
evaluation points, rather than for choosing among candidates.

Repeatedly inspecting test results and changing the model to improve them
makes that dataset another source of validation feedback. Such results should
be described as exploratory; an independent assessment may require a new
untouched dataset. Restricting access does not make previously inspected data
unseen again.

## Evaluation configuration

The existing implementation reads fixed threshold, bootstrap, and inference
settings from the `evaluation` section of `params.yaml`:

```yaml
--8<-- "params.yaml:26:33"
```

Bootstrap samples preserve the test set's positive and negative class counts.
Choose the threshold using validation evidence before examining test results.

## Outputs and review

The evaluation implementation accepts paths for:

- Sample-level predictions, including labels and raw and calibrated probabilities.
- Summary metrics and bootstrap confidence intervals.
- Confusion-matrix, ROC, and calibration plots.

Metrics include ROC AUC, average precision, accuracy, balanced accuracy,
sensitivity, specificity, precision, negative predictive value, F1, Brier score,
and expected calibration error. Sample counts, prevalence, threshold, and
configuration provide context for interpreting those results.

The pipeline tracks processed test images and sample predictions in DVC using
`rds-test`. It also generates metrics and plots in `results/evaluation/` and
copies figures and the metrics CSV into `docs/assets/evaluation/`; these reports and figure copies
are not declared DVC outputs. A maintainer should review them before publishing
reports or documentation.

## Evaluation metrics

The table reports the selected model's calibrated test metrics, using the same
metric definitions as the validation report. Lower and upper limits describe
bootstrap uncertainty at the confidence level recorded in the evaluation
context. The context also records sample counts, threshold, calibration method,
and raw Brier score and calibration error for comparison.

<!-- optional-metrics: ../../assets/evaluation/test_metrics.csv -->
> **Results not yet available.** No evaluation metrics report is available in this documentation yet.
<!-- /optional-metrics -->

The table appears automatically when `docs/assets/evaluation/test_metrics.csv`
is available. A missing report means no copy is available in this checkout,
not necessarily that evaluation has never been run. Review the approved CSV
before committing it; documentation builds do not access test data.

## Evaluation figures

Each section below shows a placeholder until its figure is available in the
current documentation checkout. The documentation build checks the files
individually and displays available figures automatically. A missing figure
means that no copy is available here; it does not establish whether evaluation
has been run elsewhere.

### Confusion matrix

The confusion matrix shows reference and predicted class counts at the fixed
calibrated probability threshold.

<!-- optional-figure: ../../assets/evaluation/confusion_matrix.png | Test confusion matrix -->
> **Results not yet available.** No confusion-matrix figure is available in this documentation yet.
<!-- /optional-figure -->

### ROC curve

The ROC curve shows sensitivity against false-positive rate across thresholds,
with ROC AUC and bootstrap uncertainty for the selected model.

<!-- optional-figure: ../../assets/evaluation/roc_curve.png | Calibrated test ROC curve -->
> **Results not yet available.** No ROC figure is available in this documentation yet.
<!-- /optional-figure -->

### Probability calibration

The reliability plots compare raw and calibrated probabilities with observed
positive frequencies, including bootstrap intervals.

<!-- optional-figure: ../../assets/evaluation/calibration_curve.png | Test probability calibration -->
> **Results not yet available.** No calibration figure is available in this documentation yet.
<!-- /optional-figure -->

After an authorised evaluation, the pipeline copies these figures and the metrics CSV into
`docs/assets/evaluation/`. Review and commit the approved copies, then rebuild
the documentation. The placeholders are replaced on the built site without
editing this page. Building documentation does not run evaluation.
