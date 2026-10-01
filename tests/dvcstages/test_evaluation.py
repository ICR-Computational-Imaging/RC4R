"""Tests for the final DVC evaluation stage."""

import csv
from pathlib import Path

import numpy as np
import torch

from dermapred.dvcstages.evaluation import EvaluationStage
from dermapred.inference.calibration import ProbabilityCalibrator
from dermapred.models.binary_classifier import LeNetBinary


def test_evaluation_stage_writes_predictions_metrics_and_figures(tmp_path: Path) -> None:
    """A small untouched split should produce every declared result."""
    model = LeNetBinary()
    model_path = tmp_path / "model.pt"
    torch.save(
        {"input_channels": 3, "model_state_dict": model.state_dict()},
        model_path,
    )
    calibrator_path = tmp_path / "calibrator.json"
    ProbabilityCalibrator.fit(
        np.linspace(-2, 2, 20), np.array([0, 1] * 10), "platt"
    ).save(calibrator_path)
    random = np.random.default_rng(42)
    images = random.uniform(-1, 1, (20, 3, 28, 28)).astype(np.float32)
    labels = np.array([[0], [1]] * 10, dtype=np.uint8)
    images_path = tmp_path / "images.npy"
    labels_path = tmp_path / "labels.npy"
    np.save(images_path, images)
    np.save(labels_path, labels)
    params_path = tmp_path / "params.yaml"
    params_path.write_text(
        "evaluation:\n"
        "  threshold: 0.5\n"
        "  bootstrap_iterations: 10\n"
        "  confidence_level: 0.95\n"
        "  reliability_bins: 4\n"
        "  inference_batch_size: 8\n"
        "  random_seed: 42\n",
        encoding="utf-8",
    )
    predictions_path = tmp_path / "results" / "predictions.csv"
    metrics_path = tmp_path / "results" / "metrics.csv"
    confusion_path = tmp_path / "results" / "confusion.png"
    roc_path = tmp_path / "results" / "roc.png"
    calibration_path = tmp_path / "results" / "calibration.png"
    documentation_figures = tmp_path / "docs" / "assets" / "evaluation"

    EvaluationStage(
        model_path,
        calibrator_path,
        images_path,
        labels_path,
        params_path,
        predictions_path,
        metrics_path,
        confusion_path,
        roc_path,
        calibration_path,
        documentation_figures,
    ).run()

    with predictions_path.open(encoding="utf-8", newline="") as predictions_file:
        assert len(list(csv.DictReader(predictions_file))) == 20
    with metrics_path.open(encoding="utf-8", newline="") as metrics_file:
        metric_names = {row["metric"] for row in csv.DictReader(metrics_file)}
    assert {"roc_auc", "accuracy", "sensitivity", "specificity"} <= metric_names
    assert confusion_path.stat().st_size > 0
    assert roc_path.stat().st_size > 0
    assert calibration_path.stat().st_size > 0
    assert (documentation_figures / "confusion.png").stat().st_size > 0
    assert (documentation_figures / "roc.png").stat().st_size > 0
    assert (documentation_figures / "calibration.png").stat().st_size > 0
