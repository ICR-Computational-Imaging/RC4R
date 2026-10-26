"""Tests for plotting model-training histories."""

from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pytest
from matplotlib.figure import Figure

from dermapred.plotting.train import plot_loss_curves


def test_plot_loss_curves_creates_image(tmp_path: Path) -> None:
    """A valid history should produce a non-empty image file."""
    history_path = tmp_path / "history.csv"
    history_path.write_text(
        "epoch,training_loss,validation_loss\n1,0.8,0.9\n2,0.6,0.7\n",
        encoding="utf-8",
    )
    output_path = tmp_path / "plots" / "loss.png"

    plot_loss_curves(history_path, output_path)

    assert output_path.stat().st_size > 0


def test_plot_loss_curves_rejects_empty_history(tmp_path: Path) -> None:
    """A header without epochs should not create a misleading graph."""
    history_path = tmp_path / "history.csv"
    history_path.write_text(
        "epoch,training_loss,validation_loss\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="at least one epoch"):
        plot_loss_curves(history_path, tmp_path / "loss.png")


def test_training_figure_has_only_validation_auc(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The AUC panel contains validation scores and marks the selected epoch."""
    original = plt.subplots
    captured: list[np.ndarray] = []

    def capture(*args: Any, **kwargs: Any) -> tuple[Figure, np.ndarray]:
        figure, axes = original(*args, **kwargs)
        captured.append(axes)
        return figure, axes

    monkeypatch.setattr(plt, "subplots", capture)
    history = tmp_path / "history.csv"
    history.write_text(
        "epoch,training_loss,validation_loss,validation_roc_auc\n1,0.8,0.7,0.6\n2,0.6,0.8,0.9\n",
        encoding="utf-8",
    )
    plot_loss_curves(history, tmp_path / "progress.png")
    auc_lines = captured[0][1].lines
    assert [line.get_label() for line in auc_lines] == ["Validation", "Selected checkpoint"]
    assert list(auc_lines[0].get_ydata()) == [0.6, 0.9]
    assert list(auc_lines[1].get_xdata()) == [1, 1]
