# Evaluating a selected model on the test set

Final test evaluation is separate from the development pipeline in
`pipelines/training/dvc.yaml`. The old `evaluate` stage, its test data tracking,
and its generated results have been removed. The evaluation Python source
remains available for a new pipeline.

## Planned evaluation pipeline

The intended location is `pipelines/evaluation/dvc.yaml`, with its own
`pipelines/evaluation/dvc.lock`. This pipeline has not yet been added. Once
configured, run it explicitly from the repository root:

```bash
uv run --group train dvc repro pipelines/evaluation/dvc.yaml
```

Set `wdir: ../..` on each stage so commands, dependencies, outputs, and parameter
paths are relative to the repository root. See
[the pipeline layout and migration steps](../../general/dvc.md#pipeline-locations-in-this-repository).

Test preprocessing can use the existing preprocessing implementation with
`--splits test`. Assign raw and processed test data and restricted evaluation
outputs to the test remote. The network or storage administrator controls who
can access it. Missing required test data should cause evaluation to fail.

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

Declare the chosen outputs in the new DVC pipeline and store restricted outputs
in the test remote. The old figures and performance summary are no longer
published on this page. A maintainer should review any new report before public
release. Omit the optional `--documentation-figures-directory` argument unless
copying figures into public documentation has been explicitly approved.
