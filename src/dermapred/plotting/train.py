"""Plot training histories produced by the model-training stage."""

from __future__ import annotations

import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402


def plot_loss_curves(history_path: Path, output_path: Path) -> None:
    """Plot training and validation loss from a training-history CSV file.

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
    figure, axes = plt.subplots(figsize=(7, 4.5))
    axes.plot(epochs, training_loss, marker="o", label="Training")
    axes.plot(epochs, validation_loss, marker="o", label="Validation")
    axes.set(xlabel="Epoch", ylabel="Weighted binary cross-entropy", title="Training loss")
    axes.grid(alpha=0.25)
    axes.legend()
    figure.tight_layout()
    figure.savefig(output_path, dpi=150)
    plt.close(figure)
