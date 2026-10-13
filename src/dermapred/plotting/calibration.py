"""Reliability plots for uncalibrated and calibrated probabilities."""

from __future__ import annotations

from pathlib import Path

import matplotlib
import numpy as np
from sklearn.calibration import calibration_curve
from sklearn.metrics import roc_auc_score, roc_curve

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402


def plot_calibration_curves(
    labels: np.ndarray,
    raw_probabilities: np.ndarray,
    calibrated_probabilities: np.ndarray,
    output_path: Path,
    bins: int,
) -> None:
    """Plot validation reliability curves before and after calibration.

    Args:
        labels: One-dimensional binary validation labels.
        raw_probabilities: Uncalibrated validation probabilities.
        calibrated_probabilities: Out-of-fold calibrated probabilities.
        output_path: Destination PNG file.
        bins: Number of equally spaced probability bins.

    Returns:
        None.

    Raises:
        OSError: If the plot cannot be written.
        ValueError: If arrays are misaligned or ``bins`` is not positive.
    """
    labels = np.asarray(labels).reshape(-1)
    raw_probabilities = np.asarray(raw_probabilities).reshape(-1)
    calibrated_probabilities = np.asarray(calibrated_probabilities).reshape(-1)
    if not (labels.shape == raw_probabilities.shape == calibrated_probabilities.shape):
        raise ValueError("Labels and probability arrays must have matching shapes.")
    if bins <= 0:
        raise ValueError("bins must be positive.")

    raw_observed, raw_predicted = calibration_curve(
        labels, raw_probabilities, n_bins=bins, strategy="uniform"
    )
    calibrated_observed, calibrated_predicted = calibration_curve(
        labels, calibrated_probabilities, n_bins=bins, strategy="uniform"
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    figure, axes = plt.subplots(figsize=(6, 6))
    axes.plot([0, 1], [0, 1], linestyle="--", color="black", label="Perfect calibration")
    axes.plot(raw_predicted, raw_observed, marker="o", label="Before calibration")
    axes.plot(
        calibrated_predicted,
        calibrated_observed,
        marker="o",
        label="After calibration (out-of-fold)",
    )
    axes.set(
        xlabel="Mean predicted probability",
        ylabel="Observed positive fraction",
        title="Validation probability calibration",
        xlim=(0, 1),
        ylim=(0, 1),
    )
    axes.grid(alpha=0.25)
    axes.legend()
    figure.tight_layout()
    figure.savefig(output_path, dpi=150)
    plt.close(figure)


def plot_validation_roc_curves(
    labels: np.ndarray,
    raw_probabilities: np.ndarray,
    calibrated_probabilities: np.ndarray,
    output_path: Path,
) -> None:
    """Plot selected-checkpoint validation ROC before and after OOF calibration.

    Args:
        labels: Binary validation reference labels.
        raw_probabilities: Uncalibrated selected-checkpoint probabilities.
        calibrated_probabilities: Out-of-fold calibrated probabilities.
        output_path: Destination PNG file.

    Raises:
        ValueError: If labels or predictions cannot define a binary ROC curve.
        OSError: If the figure cannot be written.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    figure, axes = plt.subplots(figsize=(6, 6))
    for probabilities, name in (
        (raw_probabilities, "Before calibration"),
        (calibrated_probabilities, "After calibration (out-of-fold)"),
    ):
        fpr, tpr, _ = roc_curve(labels, probabilities)
        area = roc_auc_score(labels, probabilities)
        axes.plot(fpr, tpr, label=f"{name}: AUC {area:.3f}")
    axes.plot([0, 1], [0, 1], "--", color="black", label="Chance")
    axes.set(
        xlabel="False-positive rate (1 − specificity)",
        ylabel="Sensitivity",
        title="Selected model: validation ROC",
        xlim=(0, 1),
        ylim=(0, 1),
    )
    axes.grid(alpha=0.25)
    axes.legend(loc="lower right")
    figure.tight_layout()
    figure.savefig(output_path, dpi=150)
    plt.close(figure)
