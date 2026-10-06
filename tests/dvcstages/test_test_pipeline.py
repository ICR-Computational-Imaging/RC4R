"""Exercise the checked-in test pipeline using only temporary synthetic inputs."""

import csv
import os
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import torch
import yaml

from dermapred.inference.calibration import ProbabilityCalibrator
from dermapred.models.binary_classifier import LeNetBinary


def test_test_pipeline_reproduces_with_synthetic_data(tmp_path: Path) -> None:
    """DVC connects preprocessing and evaluation without real data or remote access."""
    source_root = Path(__file__).resolve().parents[2]
    project = tmp_path / "project"
    project.mkdir()
    shutil.copytree(
        source_root / "src", project / "src", ignore=shutil.ignore_patterns("__pycache__")
    )
    for filename in ("pyproject.toml", "uv.lock", "VERSION"):
        shutil.copyfile(source_root / filename, project / filename)
    pipeline = project / "pipelines" / "test" / "dvc.yaml"
    pipeline.parent.mkdir(parents=True)
    shutil.copyfile(source_root / "pipelines" / "test" / "dvc.yaml", pipeline)

    raw = project / "data" / "raw_data" / "test"
    raw.mkdir(parents=True)
    random = np.random.default_rng(42)
    images = random.integers(0, 256, size=(20, 28, 28, 3), dtype=np.uint8)
    labels = np.array([[0], [1]] * 10, dtype=np.uint8)
    np.save(raw / "test_images.npy", images, allow_pickle=False)
    np.save(raw / "test_labels.npy", labels, allow_pickle=False)

    model_path = project / "results" / "trained_models" / "binary_classifier.pt"
    model_path.parent.mkdir(parents=True)
    # Preserve the caller's random state while constructing a repeatable checkpoint.
    with torch.random.fork_rng(devices=[]):
        torch.manual_seed(42)
        model = LeNetBinary()
    torch.save({"input_channels": 3, "model_state_dict": model.state_dict()}, model_path)
    calibrator_path = project / "results" / "calibration" / "probability_calibrator.json"
    ProbabilityCalibrator.fit(np.linspace(-2, 2, 20), np.array([0, 1] * 10), "platt").save(
        calibrator_path
    )
    (project / "params.yaml").write_text(
        yaml.safe_dump(
            {
                "evaluation": {
                    "threshold": 0.5,
                    "bootstrap_iterations": 10,
                    "confidence_level": 0.95,
                    "reliability_bins": 4,
                    "inference_batch_size": 8,
                    "random_seed": 42,
                }
            }
        ),
        encoding="utf-8",
    )

    environment = {
        **os.environ,
        "DVC_NO_ANALYTICS": "true",
        "XDG_CONFIG_HOME": str(tmp_path / "config"),
        "UV_CACHE_DIR": str(tmp_path / "uv-cache"),
        "UV_PROJECT_ENVIRONMENT": sys.prefix,
        "UV_PYTHON": sys.executable,
        "UV_NO_SYNC": "1",
        "UV_OFFLINE": "1",
        "PYTHONPATH": str(project / "src"),
        "MPLBACKEND": "Agg",
        "OMP_NUM_THREADS": "2",
        "MKL_NUM_THREADS": "2",
    }
    for arguments in (
        ["init", "--no-scm"],
        ["remote", "add", "rds-test", str(tmp_path / "remote")],
        ["repro", "pipelines/test/dvc.yaml"],
    ):
        result = subprocess.run(
            [sys.executable, "-m", "dvc", *arguments],
            cwd=project,
            env=environment,
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
        assert result.returncode == 0, result.stdout + result.stderr

    processed = np.load(project / "data" / "processed_data" / "test" / "test_images.npy")
    assert processed.shape == (20, 3, 28, 28)
    assert processed.dtype == np.float32
    evaluation = project / "results" / "evaluation"
    with (evaluation / "test_predictions.csv").open(encoding="utf-8", newline="") as stream:
        predictions = list(csv.DictReader(stream))
    assert len(predictions) == len(labels)
    assert [int(row["label"]) for row in predictions] == labels.ravel().tolist()
    with (evaluation / "test_metrics.csv").open(encoding="utf-8", newline="") as stream:
        metrics = {row["metric"]: row["value"] for row in csv.DictReader(stream)}
    assert int(metrics["sample_count"]) == len(labels)
    assert {"roc_auc", "accuracy", "sensitivity", "specificity"} <= metrics.keys()
    for filename in ("confusion_matrix.png", "roc_curve.png", "calibration_curve.png"):
        figure = evaluation / filename
        assert figure.stat().st_size > 0
        assert (project / "docs" / "assets" / "evaluation" / filename).read_bytes() == (
            figure.read_bytes()
        )
    lock = yaml.safe_load(pipeline.with_suffix(".lock").read_text())
    assert set(lock["stages"]) == {"preprocess", "evaluate"}
    assert not (project / "data" / "raw_data" / "train").exists()
