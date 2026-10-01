"""Tests for final evaluation figures."""

from pathlib import Path

import numpy as np

from dermapred.evaluation.metrics import stratified_bootstrap_indices
from dermapred.plotting.evaluation import (
    plot_calibration_curve,
    plot_confusion_matrix,
    plot_roc_curve,
)


def test_evaluation_plots_create_images(tmp_path: Path) -> None:
    """Valid test predictions should produce all three review figures."""
    labels = np.array([0, 0, 0, 1, 1, 1])
    raw = np.array([0.1, 0.2, 0.4, 0.6, 0.8, 0.9])
    calibrated = np.array([0.05, 0.15, 0.3, 0.7, 0.85, 0.95])
    bootstrap_indices = stratified_bootstrap_indices(labels, 10, 42)
    confusion_path = tmp_path / "confusion.png"
    roc_path = tmp_path / "roc.png"
    calibration_path = tmp_path / "calibration.png"

    plot_confusion_matrix(labels, calibrated, 0.5, confusion_path)
    plot_roc_curve(labels, calibrated, bootstrap_indices, 0.95, roc_path)
    plot_calibration_curve(labels, raw, calibrated, bootstrap_indices, 3, 0.95, calibration_path)

    assert confusion_path.stat().st_size > 0
    assert roc_path.stat().st_size > 0
    assert calibration_path.stat().st_size > 0
