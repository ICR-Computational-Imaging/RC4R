"""Plot training histories produced by the model-training stage."""

from __future__ import annotations

import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402


def plot_loss_curves(history_path: Path, output_path: Path) -> None:
    """Plot loss and, when available, validation ROC AUC in separate panels.

    Args:
        history_path: CSV file containing ``epoch``, ``training_loss``, and
            ``validation_loss`` columns.
        output_path: Destination for the rendered loss-curve image.

    Returns:
        None.

    Raises:
        KeyError: If a required CSV column is missing.
        OSError: If the history cannot be read or the plot cannot be written.
        ValueError: If a required value cannot be parsed or the history is
            empty.
    """
    with history_path.open(encoding="utf-8", newline="") as history_file:
        rows = list(csv.DictReader(history_file))

    if not rows:
        raise ValueError("Training history must contain at least one epoch.")

    epochs = [int(row["epoch"]) for row in rows]
    training_loss = [float(row["training_loss"]) for row in rows]
    validation_loss = [float(row["validation_loss"]) for row in rows]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    has_auc = "validation_roc_auc" in rows[0]
    figure, panels = plt.subplots(
        1, 2 if has_auc else 1, figsize=(12, 4.5) if has_auc else (7, 4.5)
    )
    axes = panels[0] if has_auc else panels
    best_epoch = epochs[min(range(len(rows)), key=lambda index: validation_loss[index])]
    axes.plot(epochs, training_loss, marker="o", label="Training")
    axes.plot(epochs, validation_loss, marker="o", label="Validation")
    axes.set(xlabel="Epoch", ylabel="Weighted binary cross-entropy", title="Training loss")
    axes.grid(alpha=0.25)
    axes.legend()
    axes.axvline(best_epoch, color="grey", linestyle=":", label="Selected checkpoint")
    axes.legend()
    if has_auc:
        auc_axes = panels[1]
        auc_axes.plot(
            epochs,
            [float(row["validation_roc_auc"]) for row in rows],
            marker="o",
            label="Validation",
        )
        auc_axes.axvline(best_epoch, color="grey", linestyle=":", label="Selected checkpoint")
        auc_axes.set(
            xlabel="Epoch", ylabel="ROC AUC", title="Validation discrimination", ylim=(0, 1)
        )
        auc_axes.grid(alpha=0.25)
        auc_axes.legend()
    figure.tight_layout()
    figure.savefig(output_path, dpi=150)
    plt.close(figure)
