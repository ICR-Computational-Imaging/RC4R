# Recording model provenance with DVC

The `provenance` stage records the identity of the trained weights and their
matching calibrator. It runs after training and calibration in the root
`dvc.yaml` pipeline. It does not use held-out test data.

## What is recorded?

The stage creates `results/trained_models/model-provenance.json`. For each
input file, it records its filename, SHA-256 hash, and size in bytes:

- Trained model weights and the final probability calibrator.
- Parameters used by the pipeline.
- Training history and validation metrics.
- `pyproject.toml` and `uv.lock`, describing the project's dependencies.

The weights hash identifies the exact checkpoint bytes. The calibrator has its
own hash because recalibration can change it without changing the weights.
The output is deterministic: identical input files produce identical JSON.
It contains no timestamp, release version, or public download URL.

This record helps check that files have not changed. It does not demonstrate
that a model has passed review or been approved for publication. The record
also does not contain all code or dataset hashes: Git history and DVC metadata
provide that wider pipeline history. Commit the updated DVC lockfile to retain
the association with this output.

## Run and store the record

From the repository root:

```bash
uv run --group train dvc repro dvc.yaml:provenance
```

DVC first checks the required upstream stages. It runs them if their inputs
have changed, then generates the provenance record. A normal `dvc repro`
also includes this stage.

The JSON is a DVC output with `cache: false`, so Git stores the file itself.
DVC still checks that it exists and records its hash in `dvc.lock`, but does
not cache it or upload it to a DVC remote. Reviewers can read it directly in
the pull request without access to the training remote.

After generating it, stage the record with the updated lockfile:

```bash
git add results/trained_models/model-provenance.json dvc.lock
```

Commit these files with the relevant code and configuration changes. When
the input files change, rerun the stage and commit the updated JSON and
lockfile. The weights and calibrator remain cached DVC outputs in `rds-train`.

## How this differs from the release manifest

Provenance is generated automatically for the current trained and calibrated
model. It can be generated before a release version is chosen.

The [release manifest](../model_download.md#prepare-a-release) is prepared
separately for the selected release. It adds the release version and public
download URLs. Its weights and calibrator hashes should match the corresponding
entries in the provenance record. The release scripts still hash the actual
files; they do not consume this provenance record automatically.
