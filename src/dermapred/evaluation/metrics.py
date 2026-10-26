"""Reusable metrics and bootstrap utilities for binary model evaluation."""

from __future__ import annotations

import numpy as np
import torch
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    balanced_accuracy_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)

from dermapred.inference.calibration import expected_calibration_error
from dermapred.models.binary_classifier import LeNetBinary

METRIC_NAMES = (
    "roc_auc",
    "average_precision",
    "accuracy",
    "balanced_accuracy",
    "sensitivity",
    "specificity",
    "precision",
    "negative_predictive_value",
    "f1_score",
    "brier_score",
    "expected_calibration_error",
)


def predict_logits(
    model: LeNetBinary,
    images: np.ndarray,
    batch_size: int,
) -> np.ndarray:
    """Run deterministic batched inference over model-ready images.

    Args:
        model: Trained binary classifier.
        images: Model-ready array with shape ``(N, C, H, W)``.
        batch_size: Maximum number of images processed together.

    Returns:
        One-dimensional NumPy array containing one logit per image.

    Raises:
        RuntimeError: If the model cannot process an image batch.
        ValueError: If the image array or batch size is invalid.
    """
    if images.ndim != 4 or images.shape[0] == 0:
        raise ValueError("Evaluation images must have shape (N, C, H, W).")
    if batch_size <= 0:
        raise ValueError("batch_size must be positive.")
    model.eval()
    predictions: list[np.ndarray] = []
    with torch.no_grad():
        for start in range(0, images.shape[0], batch_size):
            batch = torch.from_numpy(images[start : start + batch_size]).to(torch.float32)
            predictions.append(model(batch).detach().cpu().numpy().reshape(-1))
    return np.concatenate(predictions).astype(np.float64, copy=False)


def calculate_binary_metrics(
    labels: np.ndarray,
    probabilities: np.ndarray,
    threshold: float,
    reliability_bins: int,
) -> dict[str, float]:
    """Calculate discrimination, classification, and calibration metrics.

    Args:
        labels: One-dimensional binary reference labels.
        probabilities: Aligned positive-class probabilities.
        threshold: Probability at or above which a sample is classified positive.
        reliability_bins: Number of bins used for expected calibration error.

    Returns:
        Dictionary containing every supported scalar evaluation metric.

    Raises:
        ValueError: If arrays, labels, probabilities, threshold, or bins are invalid.
    """
    labels = np.asarray(labels).reshape(-1)
    probabilities = np.asarray(probabilities, dtype=np.float64).reshape(-1)
    if labels.shape != probabilities.shape or not labels.size:
        raise ValueError("Labels and probabilities must be non-empty and aligned.")
    if set(np.unique(labels).tolist()) != {0, 1}:
        raise ValueError("Evaluation labels must contain both binary classes.")
    if np.any((probabilities < 0) | (probabilities > 1)):
        raise ValueError("Probabilities must be in the range [0, 1].")
    if not 0 <= threshold <= 1 or reliability_bins <= 0:
        raise ValueError("Threshold must be in [0, 1] and bins must be positive.")

    predictions = (probabilities >= threshold).astype(np.uint8)
    true_negative, false_positive, false_negative, true_positive = confusion_matrix(
        labels, predictions, labels=[0, 1]
    ).ravel()
    specificity = true_negative / (true_negative + false_positive)
    negative_prediction_count = true_negative + false_negative
    negative_predictive_value = (
        true_negative / negative_prediction_count if negative_prediction_count else 0.0
    )
    return {
        "roc_auc": float(roc_auc_score(labels, probabilities)),
        "average_precision": float(average_precision_score(labels, probabilities)),
        "accuracy": float(accuracy_score(labels, predictions)),
        "balanced_accuracy": float(balanced_accuracy_score(labels, predictions)),
        "sensitivity": float(recall_score(labels, predictions)),
        "specificity": float(specificity),
        "precision": float(precision_score(labels, predictions, zero_division=0)),
        "negative_predictive_value": float(negative_predictive_value),
        "f1_score": float(f1_score(labels, predictions, zero_division=0)),
        "brier_score": float(brier_score_loss(labels, probabilities)),
        "expected_calibration_error": expected_calibration_error(
            labels, probabilities, reliability_bins
        ),
    }


def stratified_bootstrap_indices(
    labels: np.ndarray,
    iterations: int,
    random_seed: int,
) -> np.ndarray:
    """Generate bootstrap samples that preserve test class counts.

    Args:
        labels: One-dimensional binary reference labels.
        iterations: Number of bootstrap resamples.
        random_seed: Seed for the NumPy random generator.

    Returns:
        Integer array with shape ``(iterations, N)`` containing sample indices.

    Raises:
        ValueError: If labels lack either class or numerical settings are invalid.
    """
    labels = np.asarray(labels).reshape(-1)
    negative_indices = np.flatnonzero(labels == 0)
    positive_indices = np.flatnonzero(labels == 1)
    if not negative_indices.size or not positive_indices.size:
        raise ValueError("Bootstrap labels must contain both binary classes.")
    if iterations <= 0 or random_seed < 0:
        raise ValueError("Iterations must be positive and the seed non-negative.")
    random = np.random.default_rng(random_seed)
    samples = np.empty((iterations, labels.size), dtype=np.int64)
    for iteration in range(iterations):
        sampled_negative = random.choice(negative_indices, negative_indices.size, replace=True)
        sampled_positive = random.choice(positive_indices, positive_indices.size, replace=True)
        combined = np.concatenate((sampled_negative, sampled_positive))
        random.shuffle(combined)
        samples[iteration] = combined
    return samples


def bootstrap_metric_intervals(
    labels: np.ndarray,
    probabilities: np.ndarray,
    bootstrap_indices: np.ndarray,
    threshold: float,
    reliability_bins: int,
    confidence_level: float,
) -> dict[str, tuple[float, float]]:
    """Calculate percentile bootstrap intervals for every evaluation metric.

    Args:
        labels: One-dimensional binary reference labels.
        probabilities: Aligned positive-class probabilities.
        bootstrap_indices: Resampling indices from ``stratified_bootstrap_indices``.
        threshold: Fixed classification threshold.
        reliability_bins: Number of bins used for expected calibration error.
        confidence_level: Central interval width between zero and one.

    Returns:
        Mapping from metric name to lower and upper confidence limits.

    Raises:
        ValueError: If confidence level or bootstrap dimensions are invalid.
    """
    labels = np.asarray(labels).reshape(-1)
    probabilities = np.asarray(probabilities, dtype=np.float64).reshape(-1)
    bootstrap_indices = np.asarray(bootstrap_indices)
    if labels.shape != probabilities.shape:
        raise ValueError("Labels and probabilities must be aligned.")
    if not 0 < confidence_level < 1:
        raise ValueError("confidence_level must be between zero and one.")
    if bootstrap_indices.ndim != 2 or bootstrap_indices.shape[1] != len(labels):
        raise ValueError("Bootstrap indices must have shape (iterations, samples).")
    values: dict[str, list[float]] = {name: [] for name in METRIC_NAMES}
    for indices in bootstrap_indices:
        metrics = calculate_binary_metrics(
            labels[indices], probabilities[indices], threshold, reliability_bins
        )
        for name, value in metrics.items():
            values[name].append(value)
    tail = (1.0 - confidence_level) / 2.0
    return {
        name: (
            float(np.quantile(metric_values, tail)),
            float(np.quantile(metric_values, 1.0 - tail)),
        )
        for name, metric_values in values.items()
    }
