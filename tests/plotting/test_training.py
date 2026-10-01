"""Tests for plotting model-training histories."""

from pathlib import Path

import pytest

from dermapred.plotting.training import plot_loss_curves


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
