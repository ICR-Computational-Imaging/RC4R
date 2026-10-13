"""Tests for validation calibration plots."""

from pathlib import Path

import numpy as np

from dermapred.plotting.calibration import plot_calibration_curves


def test_plot_calibration_curves_creates_png(tmp_path: Path) -> None:
    """Aligned validation probabilities should produce a visible PNG."""
    labels = np.array([0, 0, 0, 1, 1, 1])
    raw = np.array([0.1, 0.2, 0.4, 0.5, 0.7, 0.9])
    calibrated = np.array([0.0, 0.1, 0.2, 0.7, 0.8, 1.0])
    output_path = tmp_path / "calibration.png"

    plot_calibration_curves(labels, raw, calibrated, output_path, bins=3)

    assert output_path.stat().st_size > 0
