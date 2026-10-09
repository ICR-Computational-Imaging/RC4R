"""Tests for the DVC model-training stage."""

import csv
from pathlib import Path

import numpy as np
import torch
from sklearn.metrics import roc_auc_score

from dermapred.dvcstages.train import TrainingStage, load_training_parameters
from dermapred.models.binary_classifier import LeNetBinary


def _write_parameters(path: Path, epochs: int = 1) -> None:
    """Write a minimal training configuration for a test stage."""
    path.write_text(
        "train:\n"
        "  batch_size: 2\n"
        f"  epochs: {epochs}\n"
        "  learning_rate: 0.001\n"
        "  random_seed: 42\n"
        "  num_workers: 0\n"
        "  augmentation:\n"
        "    horizontal_flip_probability: 0.5\n"
        "    vertical_flip_probability: 0.5\n"
        "    rotation_probability: 0.5\n",
        encoding="utf-8",
    )


def test_load_training_parameters_reads_configuration(tmp_path: Path) -> None:
    """The YAML loader should return validated training settings."""
    params_path = tmp_path / "params.yaml"
    _write_parameters(params_path, epochs=3)

    parameters = load_training_parameters(params_path)

    assert parameters.batch_size == 2
    assert parameters.epochs == 3
    assert parameters.rotation_probability == 0.5


def test_training_stage_writes_checkpoint_history_and_plot(tmp_path: Path) -> None:
    """A short training run should create every declared stage output."""
    random = np.random.default_rng(42)
    train_images = random.uniform(-1, 1, (4, 3, 28, 28)).astype(np.float32)
    validation_images = random.uniform(-1, 1, (2, 3, 28, 28)).astype(np.float32)
    train_labels = np.array([[0], [1], [0], [1]], dtype=np.uint8)
    validation_labels = np.array([[0], [1]], dtype=np.uint8)

    train_images_path = tmp_path / "train_images.npy"
    train_labels_path = tmp_path / "train_labels.npy"
    validation_images_path = tmp_path / "validation_images.npy"
    validation_labels_path = tmp_path / "validation_labels.npy"
    np.save(train_images_path, train_images)
    np.save(train_labels_path, train_labels)
    np.save(validation_images_path, validation_images)
    np.save(validation_labels_path, validation_labels)

    params_path = tmp_path / "params.yaml"
    _write_parameters(params_path)
    model_path = tmp_path / "results" / "model.pt"
    history_path = tmp_path / "results" / "history.csv"
    plot_path = tmp_path / "results" / "loss.png"

    TrainingStage(
        train_images_path,
        train_labels_path,
        validation_images_path,
        validation_labels_path,
        params_path,
        model_path,
        history_path,
        plot_path,
        tmp_path / "docs",
    ).run()

    checkpoint = torch.load(model_path, map_location="cpu", weights_only=True)
    assert checkpoint["best_epoch"] == 1
    assert checkpoint["image_size"] == [28, 28]
    assert "model_state_dict" in checkpoint
    with history_path.open(encoding="utf-8", newline="") as history_file:
        rows = list(csv.DictReader(history_file))
    assert len(rows) == 1
    assert set(rows[0]) == {"epoch", "training_loss", "validation_loss", "validation_roc_auc"}
    model = LeNetBinary()
    model.load_state_dict(checkpoint["model_state_dict"])
    model.eval()
    with torch.no_grad():
        scores = model(torch.from_numpy(validation_images)).numpy().reshape(-1)
    assert float(rows[0]["validation_roc_auc"]) == roc_auc_score(
        validation_labels.reshape(-1), scores
    )
    assert (tmp_path / "docs" / "training_progress.png").read_bytes() == plot_path.read_bytes()
    assert plot_path.stat().st_size > 0
