"""Tests for reusable final-evaluation calculations."""

import numpy as np

from dermapred.evaluation.metrics import (
    bootstrap_metric_intervals,
    calculate_binary_metrics,
    stratified_bootstrap_indices,
)


def test_binary_metrics_and_bootstrap_intervals() -> None:
    """Metrics and intervals should cover a correctly classified example."""
    labels = np.array([0, 0, 0, 1, 1, 1])
    probabilities = np.array([0.05, 0.2, 0.4, 0.6, 0.8, 0.95])
    bootstrap_indices = stratified_bootstrap_indices(labels, iterations=20, random_seed=42)

    metrics = calculate_binary_metrics(labels, probabilities, threshold=0.5, reliability_bins=3)
    intervals = bootstrap_metric_intervals(
        labels,
        probabilities,
        bootstrap_indices,
        threshold=0.5,
        reliability_bins=3,
        confidence_level=0.95,
    )

    assert metrics["accuracy"] == 1.0
    assert metrics["sensitivity"] == 1.0
    assert metrics["specificity"] == 1.0
    assert intervals["roc_auc"] == (1.0, 1.0)
