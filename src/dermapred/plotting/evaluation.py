"""Plots used to review performance on the untouched test set."""

from __future__ import annotations

from pathlib import Path

import matplotlib
import numpy as np
from sklearn.metrics import confusion_matrix, roc_auc_score, roc_curve

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402


def plot_confusion_matrix(
    labels: np.ndarray,
    probabilities: np.ndarray,
    threshold: float,
    output_path: Path,
    dataset_name: str = "Test",
) -> None:
    """Plot test confusion-matrix counts at a fixed probability threshold.

    Args:
        labels: One-dimensional binary test labels.
        probabilities: Aligned calibrated probabilities.
        threshold: Fixed positive-classification threshold.
        output_path: Destination PNG file.
        dataset_name: Dataset label used in the confusion-matrix title.

    Returns:
        None.

    Raises:
        OSError: If the plot cannot be written.
        ValueError: If arrays are misaligned or threshold is invalid.
    """
    labels = np.asarray(labels).reshape(-1)
    probabilities = np.asarray(probabilities).reshape(-1)
    if labels.shape != probabilities.shape or not 0 <= threshold <= 1:
        raise ValueError("Inputs must be aligned and threshold must be in [0, 1].")
    matrix = confusion_matrix(labels, probabilities >= threshold, labels=[0, 1])
    output_path.parent.mkdir(parents=True, exist_ok=True)
    figure, axes = plt.subplots(figsize=(5.5, 5))
    image = axes.imshow(matrix, cmap="Blues")
    for row in range(2):
        for column in range(2):
            axes.text(column, row, str(matrix[row, column]), ha="center", va="center")
    axes.set(
        xticks=[0, 1],
        yticks=[0, 1],
        xticklabels=["Benign", "Concerning"],
        yticklabels=["Benign", "Concerning"],
        xlabel="Predicted class",
        ylabel="Reference class",
        title=f"{dataset_name} confusion matrix (threshold = {threshold:.2f})",
    )
    figure.colorbar(image, ax=axes, fraction=0.046, pad=0.04)
    figure.tight_layout()
    figure.savefig(output_path, dpi=150)
    plt.close(figure)


def plot_roc_curve(
    labels: np.ndarray,
    probabilities: np.ndarray,
    bootstrap_indices: np.ndarray,
    confidence_level: float,
    output_path: Path,
) -> None:
    """Plot the calibrated test ROC curve with a bootstrap confidence band.

    Args:
        labels: One-dimensional binary test labels.
        probabilities: Aligned calibrated probabilities.
        bootstrap_indices: Stratified bootstrap sample indices.
        confidence_level: Central confidence-band width.
        output_path: Destination PNG file.

    Returns:
        None.

    Raises:
        OSError: If the plot cannot be written.
        ValueError: If inputs or confidence level are invalid.
    """
    labels = np.asarray(labels).reshape(-1)
    probabilities = np.asarray(probabilities).reshape(-1)
    if labels.shape != probabilities.shape or not 0 < confidence_level < 1:
        raise ValueError("ROC inputs or confidence level are invalid.")
    false_positive_rate, true_positive_rate, _ = roc_curve(labels, probabilities)
    grid = np.linspace(0, 1, 201)
    bootstrapped_rates = []
    bootstrap_areas = []
    for indices in bootstrap_indices:
        bootstrap_fpr, bootstrap_tpr, _ = roc_curve(labels[indices], probabilities[indices])
        bootstrapped_rates.append(np.interp(grid, bootstrap_fpr, bootstrap_tpr))
        bootstrap_areas.append(roc_auc_score(labels[indices], probabilities[indices]))
    tail = (1.0 - confidence_level) / 2.0
    lower_rate, upper_rate = np.quantile(bootstrapped_rates, [tail, 1 - tail], axis=0)
    lower_area, upper_area = np.quantile(bootstrap_areas, [tail, 1 - tail])
    area = roc_auc_score(labels, probabilities)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    figure, axes = plt.subplots(figsize=(6, 6))
    axes.plot([0, 1], [0, 1], linestyle="--", color="black", label="Chance")
    axes.plot(
        false_positive_rate,
        true_positive_rate,
        label=f"ROC AUC {area:.3f} ({lower_area:.3f}–{upper_area:.3f})",
    )
    axes.fill_between(grid, lower_rate, upper_rate, alpha=0.2, label="Bootstrap interval")
    axes.set(
        xlabel="False-positive rate",
        ylabel="True-positive rate",
        title="Calibrated test ROC curve",
        xlim=(0, 1),
        ylim=(0, 1),
    )
    axes.grid(alpha=0.25)
    axes.legend(loc="lower right")
    figure.tight_layout()
    figure.savefig(output_path, dpi=150)
    plt.close(figure)


def _calibration_points(
    labels: np.ndarray,
    probabilities: np.ndarray,
    bootstrap_indices: np.ndarray,
    bins: int,
    confidence_level: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Calculate fixed-bin reliability points and bootstrap intervals.

    Args:
        labels: One-dimensional binary reference labels.
        probabilities: Aligned positive-class probabilities.
        bootstrap_indices: Stratified bootstrap sample indices.
        bins: Number of fixed equal-width probability bins.
        confidence_level: Central confidence-interval width.

    Returns:
        Mean prediction, observed fraction, lower and upper limits, and count
        arrays with one entry per bin.

    Raises:
        ValueError: If NumPy cannot process incompatible array dimensions.
    """
    edges = np.linspace(0, 1, bins + 1)
    assignments = np.minimum(np.digitize(probabilities, edges[1:-1]), bins - 1)
    means = np.full(bins, np.nan)
    observed = np.full(bins, np.nan)
    counts = np.zeros(bins, dtype=int)
    bootstrap_observed = np.full((bootstrap_indices.shape[0], bins), np.nan)
    for index in range(bins):
        mask = assignments == index
        counts[index] = int(mask.sum())
        if counts[index]:
            means[index] = probabilities[mask].mean()
            observed[index] = labels[mask].mean()
        for iteration, sample_indices in enumerate(bootstrap_indices):
            sampled_mask = assignments[sample_indices] == index
            if np.any(sampled_mask):
                bootstrap_observed[iteration, index] = labels[sample_indices][sampled_mask].mean()
    tail = (1.0 - confidence_level) / 2.0
    lower = np.full(bins, np.nan)
    upper = np.full(bins, np.nan)
    for index in range(bins):
        valid_bootstrap = bootstrap_observed[:, index]
        valid_bootstrap = valid_bootstrap[np.isfinite(valid_bootstrap)]
        if valid_bootstrap.size:
            lower[index], upper[index] = np.quantile(valid_bootstrap, [tail, 1 - tail])
    return means, observed, lower, upper, counts


def plot_calibration_curve(
    labels: np.ndarray,
    raw_probabilities: np.ndarray,
    calibrated_probabilities: np.ndarray,
    bootstrap_indices: np.ndarray,
    bins: int,
    confidence_level: float,
    output_path: Path,
) -> None:
    """Plot test reliability before and after calibration with uncertainty.

    Args:
        labels: One-dimensional binary test labels.
        raw_probabilities: Uncalibrated model probabilities.
        calibrated_probabilities: Probabilities from the validation calibrator.
        bootstrap_indices: Stratified bootstrap sample indices.
        bins: Number of fixed equal-width probability bins.
        confidence_level: Central confidence-interval width.
        output_path: Destination PNG file.

    Returns:
        None.

    Raises:
        OSError: If the plot cannot be written.
        ValueError: If arrays, bins, or confidence level are invalid.
    """
    labels = np.asarray(labels).reshape(-1)
    raw_probabilities = np.asarray(raw_probabilities).reshape(-1)
    calibrated_probabilities = np.asarray(calibrated_probabilities).reshape(-1)
    if not (labels.shape == raw_probabilities.shape == calibrated_probabilities.shape):
        raise ValueError("Calibration arrays must have matching shapes.")
    if bins <= 0 or not 0 < confidence_level < 1:
        raise ValueError("Bins and confidence level are invalid.")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    figure, axes = plt.subplots(1, 2, figsize=(12, 5.5), sharex=True, sharey=True)
    for axis, probabilities, title in zip(
        axes,
        (raw_probabilities, calibrated_probabilities),
        ("Before calibration", "After calibration"),
        strict=True,
    ):
        means, observed, lower, upper, counts = _calibration_points(
            labels, probabilities, bootstrap_indices, bins, confidence_level
        )
        valid = np.isfinite(means) & np.isfinite(observed) & np.isfinite(lower) & np.isfinite(upper)
        errors = np.vstack(
            (
                np.maximum(0, observed[valid] - lower[valid]),
                np.maximum(0, upper[valid] - observed[valid]),
            )
        )
        axis.plot([0, 1], [0, 1], linestyle="--", color="black", label="Perfect")
        axis.errorbar(means[valid], observed[valid], yerr=errors, marker="o", capsize=3)
        for x_value, y_value, count in zip(
            means[valid], observed[valid], counts[valid], strict=True
        ):
            axis.annotate(
                f"n={count}",
                (x_value, y_value),
                xytext=(4, 5),
                textcoords="offset points",
            )
        axis.set(title=title, xlabel="Mean predicted probability", xlim=(0, 1), ylim=(0, 1))
        axis.grid(alpha=0.25)
    axes[0].set_ylabel("Observed positive fraction")
    figure.suptitle("Test probability calibration with bootstrap intervals")
    figure.tight_layout()
    figure.savefig(output_path, dpi=150)
    plt.close(figure)
