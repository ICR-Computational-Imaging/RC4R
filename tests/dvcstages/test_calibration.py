"""Tests for the DVC probability-calibration stage."""

import json
from pathlib import Path

import numpy as np
import pytest
import torch

from dermapred.dvcstages.calibration import (
    CalibrationParameters,
    CalibrationStage,
    cross_validated_probabilities,
    predict_logits,
)
from dermapred.evaluation.metrics import METRIC_NAMES, calculate_binary_metrics
from dermapred.models.binary_classifier import LeNetBinary


@pytest.mark.parametrize("method", ["isotonic", "platt"])
def test_cross_validated_probabilities_cover_every_sample(method: str) -> None:
    """Every validation sample should receive an out-of-fold probability."""
    logits = np.linspace(-3, 3, 20)
    labels = np.array([0, 1] * 10)
    parameters = CalibrationParameters(method, 5, 5, 8, 42)

    probabilities = cross_validated_probabilities(logits, labels, parameters)

    assert probabilities.shape == labels.shape
    assert np.all((probabilities >= 0) & (probabilities <= 1))


def test_calibration_stage_writes_mapping_metrics_and_plot(tmp_path: Path) -> None:
    """The stage should produce reusable calibration and review artifacts."""
    model = LeNetBinary()
    model_path = tmp_path / "model.pt"
    torch.save(
        {"input_channels": 3, "model_state_dict": model.state_dict()},
        model_path,
    )
    random = np.random.default_rng(42)
    images = random.uniform(-1, 1, (20, 3, 28, 28)).astype(np.float32)
    labels = np.array([[0], [1]] * 10, dtype=np.uint8)
    images_path = tmp_path / "images.npy"
    labels_path = tmp_path / "labels.npy"
    np.save(images_path, images)
    np.save(labels_path, labels)
    params_path = tmp_path / "params.yaml"
    params_path.write_text(
        "evaluation:\n  threshold: 0.7\n"
        "calibration:\n"
        "  method: isotonic\n"
        "  cross_validation_folds: 5\n"
        "  reliability_bins: 5\n"
        "  inference_batch_size: 8\n"
        "  random_seed: 42\n",
        encoding="utf-8",
    )
    calibrator_path = tmp_path / "results" / "calibrator.json"
    metrics_path = tmp_path / "results" / "metrics.json"
    plot_path = tmp_path / "results" / "calibration.png"

    CalibrationStage(
        model_path,
        images_path,
        labels_path,
        params_path,
        calibrator_path,
        metrics_path,
        plot_path,
        tmp_path / "docs",
    ).run()

    assert json.loads(calibrator_path.read_text(encoding="utf-8"))["method"] == "isotonic"
    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    assert metrics["cross_validation_folds"] == 5
    assert plot_path.stat().st_size > 0

    assert metrics["threshold"] == 0.7
    assert metrics["sample_count"] == 20
    assert set(metrics["after_calibration_out_of_fold"]) == set(METRIC_NAMES)
    for artifact in ("validation_roc.png", "validation_confusion_matrix.png", "metrics.md"):
        assert (tmp_path / "docs" / artifact).stat().st_size > 0

    oof_probabilities = cross_validated_probabilities(
        predict_logits(model, images, 8),
        labels,
        CalibrationParameters("isotonic", 5, 5, 8, 42),
    )
    assert metrics["after_calibration_out_of_fold"] == calculate_binary_metrics(
        labels, oof_probabilities, 0.7, 5
    )
