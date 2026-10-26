"""DVC stage for training the DermaPred binary classifier."""

from __future__ import annotations

import argparse
import csv
import shutil
from collections.abc import Callable, Sequence
from pathlib import Path

import numpy as np
import torch
import yaml
from monai.data.dataloader import DataLoader
from monai.transforms.compose import Compose
from monai.transforms.spatial.array import RandFlip, RandRotate90
from monai.utils.misc import set_determinism
from sklearn.metrics import roc_auc_score
from torch import nn
from torch.utils.data import Dataset
from tqdm import tqdm

from dermapred.models.binary_classifier import LeNetBinary
from dermapred.plotting.train import plot_loss_curves


class TrainingParameters:
    """Validated parameters used by the model-training stage."""

    def __init__(
        self,
        batch_size: int,
        epochs: int,
        learning_rate: float,
        random_seed: int,
        num_workers: int,
        horizontal_flip_probability: float,
        vertical_flip_probability: float,
        rotation_probability: float,
    ) -> None:
        """Store and validate model-training parameters.

        Args:
            batch_size: Number of samples in each optimisation batch.
            epochs: Number of complete passes over the training data.
            learning_rate: Adam optimiser learning rate.
            random_seed: Seed used by NumPy, PyTorch, MONAI, and data loading.
            num_workers: Number of worker processes used by each data loader.
            horizontal_flip_probability: Probability of a horizontal flip.
            vertical_flip_probability: Probability of a vertical flip.
            rotation_probability: Probability of a random 90-degree rotation.

        Returns:
            None.

        Raises:
            ValueError: If a count, rate, seed, worker count, or probability
                falls outside its permitted range.
        """
        if batch_size <= 0 or epochs <= 0:
            raise ValueError("batch_size and epochs must be positive integers.")
        if learning_rate <= 0:
            raise ValueError("learning_rate must be positive.")
        if random_seed < 0 or num_workers < 0:
            raise ValueError("random_seed and num_workers must be non-negative integers.")
        probabilities = (
            horizontal_flip_probability,
            vertical_flip_probability,
            rotation_probability,
        )
        if any(probability < 0 or probability > 1 for probability in probabilities):
            raise ValueError("Augmentation probabilities must be between zero and one.")

        self.batch_size = batch_size
        self.epochs = epochs
        self.learning_rate = learning_rate
        self.random_seed = random_seed
        self.num_workers = num_workers
        self.horizontal_flip_probability = horizontal_flip_probability
        self.vertical_flip_probability = vertical_flip_probability
        self.rotation_probability = rotation_probability

    def as_dict(self) -> dict[str, int | float]:
        """Return serialisable training parameters for the model checkpoint.

        Returns:
            Dictionary containing every validated training parameter.

        Raises:
            RuntimeError: If an attribute cannot be read from this instance.
        """
        return {
            "batch_size": self.batch_size,
            "epochs": self.epochs,
            "learning_rate": self.learning_rate,
            "random_seed": self.random_seed,
            "num_workers": self.num_workers,
            "horizontal_flip_probability": self.horizontal_flip_probability,
            "vertical_flip_probability": self.vertical_flip_probability,
            "rotation_probability": self.rotation_probability,
        }


class ImageArrayDataset(Dataset[tuple[torch.Tensor, torch.Tensor]]):
    """Expose aligned NumPy image and label arrays to a PyTorch data loader."""

    def __init__(
        self,
        images: np.ndarray,
        labels: np.ndarray,
        transform: Callable[[torch.Tensor], torch.Tensor] | None = None,
    ) -> None:
        """Configure an in-memory image dataset.

        Args:
            images: Model-ready image array with shape ``(N, C, H, W)``.
            labels: Binary labels with shape ``(N,)`` or ``(N, 1)``.
            transform: Optional transform applied independently to each image.

        Returns:
            None.

        Raises:
            ValueError: If images and labels contain different sample counts.
        """
        if images.shape[0] != labels.shape[0]:
            raise ValueError("Image and label arrays must contain the same samples.")
        self.images = images
        self.labels = labels.reshape(-1, 1)
        self.transform = transform

    def __len__(self) -> int:
        """Return the number of samples in the dataset.

        Returns:
            Number of aligned image-label pairs.

        Raises:
            RuntimeError: If the image array does not expose a leading dimension.
        """
        return int(self.images.shape[0])

    def __getitem__(self, index: int) -> tuple[torch.Tensor, torch.Tensor]:
        """Return one image and its binary label.

        Args:
            index: Zero-based sample index.

        Returns:
            Image tensor and a one-element floating label tensor.

        Raises:
            IndexError: If ``index`` is outside the dataset.
            RuntimeError: If the configured transform cannot process the image.
        """
        image = torch.from_numpy(self.images[index]).to(dtype=torch.float32)
        label = torch.from_numpy(self.labels[index]).to(dtype=torch.float32)
        if self.transform is not None:
            image = self.transform(image)
        return image, label


def load_training_parameters(params_path: Path) -> TrainingParameters:
    """Load the training section from a YAML parameters file.

    Args:
        params_path: YAML file containing the ``train`` configuration.

    Returns:
        Validated training parameters.

    Raises:
        OSError: If the parameters file cannot be read.
        TypeError: If parameter values have incompatible types.
        ValueError: If required parameters are missing or invalid.
    """
    try:
        parameters = yaml.safe_load(params_path.read_text(encoding="utf-8"))["train"]
        augmentation = parameters["augmentation"]
        return TrainingParameters(
            batch_size=int(parameters["batch_size"]),
            epochs=int(parameters["epochs"]),
            learning_rate=float(parameters["learning_rate"]),
            random_seed=int(parameters["random_seed"]),
            num_workers=int(parameters["num_workers"]),
            horizontal_flip_probability=float(augmentation["horizontal_flip_probability"]),
            vertical_flip_probability=float(augmentation["vertical_flip_probability"]),
            rotation_probability=float(augmentation["rotation_probability"]),
        )
    except (KeyError, TypeError, yaml.YAMLError) as error:
        raise ValueError(f"Invalid training configuration in {params_path}.") from error


def build_training_transform(parameters: TrainingParameters) -> Compose:
    """Build deterministic-seed MONAI augmentation for training images.

    Args:
        parameters: Validated augmentation probabilities and random seed.

    Returns:
        MONAI composition of random flips and 90-degree rotations.

    Raises:
        ValueError: If MONAI rejects an augmentation parameter.
    """
    transform = Compose(
        [
            RandFlip(prob=parameters.horizontal_flip_probability, spatial_axis=1),
            RandFlip(prob=parameters.vertical_flip_probability, spatial_axis=0),
            RandRotate90(prob=parameters.rotation_probability, max_k=3, spatial_axes=(0, 1)),
        ]
    )
    transform.set_random_state(seed=parameters.random_seed)
    return transform


def validate_training_arrays(images: np.ndarray, labels: np.ndarray, name: str) -> None:
    """Validate one model-ready image array and its binary labels.

    Args:
        images: Image array expected to have shape ``(N, 3, H, W)``.
        labels: Binary label array expected to contain one label per image.
        name: Human-readable split name used in error messages.

    Returns:
        None.

    Raises:
        ValueError: If shapes, values, data types, or sample counts are invalid.
    """
    if images.ndim != 4 or images.shape[1] != 3:
        raise ValueError(f"{name} images must have shape (N, 3, H, W).")
    if images.shape[0] == 0 or images.shape[0] != labels.reshape(-1).shape[0]:
        raise ValueError(f"{name} images and labels must contain the same samples.")
    if not np.issubdtype(images.dtype, np.floating) or not np.isfinite(images).all():
        raise ValueError(f"{name} images must contain finite floating values.")
    if images.min() < -1 or images.max() > 1:
        raise ValueError(f"{name} image values must be in the range [-1, 1].")
    if set(np.unique(labels).tolist()) - {0, 1}:
        raise ValueError(f"{name} labels must contain only zero and one.")


class TrainingStage:
    """Train and save the DermaPred proof-of-concept classifier."""

    def __init__(
        self,
        train_images: Path,
        train_labels: Path,
        validation_images: Path,
        validation_labels: Path,
        params_path: Path,
        model_output: Path,
        history_output: Path,
        plot_output: Path,
        documentation_figures_directory: Path | None = None,
    ) -> None:
        """Configure training inputs, parameters, and outputs.

        Args:
            train_images: Processed training-image array.
            train_labels: Binary training-label array.
            validation_images: Processed validation-image array.
            validation_labels: Binary validation-label array.
            params_path: YAML file containing training parameters.
            model_output: Destination for the best model checkpoint.
            history_output: Destination for per-epoch loss values.
            plot_output: Destination for the rendered loss curves.
            documentation_figures_directory: Optional directory for review copies
                of generated figures.

        Returns:
            None.

        Raises:
            TypeError: If any path is not a ``pathlib.Path`` object.
        """
        paths = (
            train_images,
            train_labels,
            validation_images,
            validation_labels,
            params_path,
            model_output,
            history_output,
            plot_output,
        )
        if not all(isinstance(path, Path) for path in paths):
            raise TypeError("Training stage paths must be pathlib.Path objects.")
        self.train_images = train_images
        self.train_labels = train_labels
        self.validation_images = validation_images
        self.validation_labels = validation_labels
        self.params_path = params_path
        self.model_output = model_output
        self.history_output = history_output
        self.plot_output = plot_output
        self.documentation_figures_directory = documentation_figures_directory

    def run(self) -> None:
        """Train the classifier and write its checkpoint and loss history.

        Returns:
            None.

        Raises:
            OSError: If an input cannot be read or an output cannot be written.
            RuntimeError: If PyTorch or MONAI cannot execute training.
            TypeError: If training parameters or arrays have incompatible types.
            ValueError: If parameters, input arrays, or labels are invalid.
        """
        parameters = load_training_parameters(self.params_path)
        set_determinism(seed=parameters.random_seed)
        np.random.seed(parameters.random_seed)
        torch.manual_seed(parameters.random_seed)

        train_images = np.load(self.train_images, allow_pickle=False)
        train_labels = np.load(self.train_labels, allow_pickle=False)
        validation_images = np.load(self.validation_images, allow_pickle=False)
        validation_labels = np.load(self.validation_labels, allow_pickle=False)
        validate_training_arrays(train_images, train_labels, "Training")
        validate_training_arrays(validation_images, validation_labels, "Validation")
        if set(np.unique(validation_labels).tolist()) != {0, 1}:
            raise ValueError("Validation labels must contain both classes for ROC AUC.")

        train_dataset = ImageArrayDataset(
            train_images,
            train_labels,
            transform=build_training_transform(parameters),
        )
        validation_dataset = ImageArrayDataset(validation_images, validation_labels)
        generator = torch.Generator().manual_seed(parameters.random_seed)
        train_loader = DataLoader(
            train_dataset,
            batch_size=parameters.batch_size,
            shuffle=True,
            num_workers=parameters.num_workers,
            generator=generator,
        )
        validation_loader = DataLoader(
            validation_dataset,
            batch_size=parameters.batch_size,
            shuffle=False,
            num_workers=parameters.num_workers,
        )

        model = LeNetBinary(input_channels=int(train_images.shape[1]))
        negative_count = int(np.count_nonzero(train_labels == 0))
        positive_count = int(np.count_nonzero(train_labels == 1))
        if positive_count == 0 or negative_count == 0:
            raise ValueError("Training labels must contain both binary classes.")
        positive_weight = torch.tensor([negative_count / positive_count], dtype=torch.float32)
        criterion = nn.BCEWithLogitsLoss(pos_weight=positive_weight)
        optimiser = torch.optim.Adam(model.parameters(), lr=parameters.learning_rate)

        history: list[dict[str, int | float]] = []
        best_validation_loss = float("inf")
        best_epoch = 0
        best_state: dict[str, torch.Tensor] | None = None

        for epoch in tqdm(range(1, parameters.epochs + 1), desc="Training"):
            model.train()
            training_loss_total = 0.0
            for images, labels in train_loader:
                optimiser.zero_grad(set_to_none=True)
                loss = criterion(model(images), labels)
                loss.backward()
                optimiser.step()
                training_loss_total += float(loss.item()) * images.shape[0]

            model.eval()
            validation_loss_total = 0.0
            validation_scores: list[np.ndarray] = []
            with torch.no_grad():
                for images, labels in validation_loader:
                    logits = model(images)
                    validation_scores.append(logits.cpu().numpy().reshape(-1))
                    validation_loss = criterion(logits, labels)
                    validation_loss_total += float(validation_loss.item()) * images.shape[0]

            training_loss = training_loss_total / len(train_dataset)
            validation_loss = validation_loss_total / len(validation_dataset)
            history.append(
                {
                    "epoch": epoch,
                    "training_loss": training_loss,
                    "validation_loss": validation_loss,
                    "validation_roc_auc": float(
                        roc_auc_score(
                            validation_labels.reshape(-1), np.concatenate(validation_scores)
                        )
                    ),
                }
            )
            if validation_loss < best_validation_loss:
                best_validation_loss = validation_loss
                best_epoch = epoch
                best_state = {
                    name: value.detach().cpu().clone() for name, value in model.state_dict().items()
                }

        if best_state is None:
            raise RuntimeError("Training did not produce a model checkpoint.")

        self.history_output.parent.mkdir(parents=True, exist_ok=True)
        with self.history_output.open("w", encoding="utf-8", newline="") as history_file:
            writer = csv.DictWriter(
                history_file,
                fieldnames=["epoch", "training_loss", "validation_loss", "validation_roc_auc"],
            )
            writer.writeheader()
            writer.writerows(history)

        self.model_output.parent.mkdir(parents=True, exist_ok=True)
        torch.save(
            {
                "model_state_dict": best_state,
                "input_channels": int(train_images.shape[1]),
                "image_size": [int(train_images.shape[2]), int(train_images.shape[3])],
                "best_epoch": best_epoch,
                "best_validation_loss": best_validation_loss,
                "training_parameters": parameters.as_dict(),
            },
            self.model_output,
        )
        plot_loss_curves(self.history_output, self.plot_output)
        if self.documentation_figures_directory is not None:
            self.documentation_figures_directory.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(
                self.plot_output, self.documentation_figures_directory / "training_progress.png"
            )


def _parse_args(arguments: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments for the training stage.

    Args:
        arguments: Optional command-line arguments. When omitted, arguments
            are read from ``sys.argv``.

    Returns:
        Parsed paths for every training input and output.

    Raises:
        SystemExit: If a required argument is missing or invalid.
    """
    parser = argparse.ArgumentParser(description="Train the DermaPred binary classifier.")
    for option in (
        "train-images",
        "train-labels",
        "validation-images",
        "validation-labels",
        "params-path",
        "model-output",
        "history-output",
        "plot-output",
    ):
        parser.add_argument(f"--{option}", type=Path, required=True)
    parser.add_argument("--documentation-figures-directory", type=Path)
    return parser.parse_args(arguments)


if __name__ == "__main__":
    arguments = _parse_args()
    stage = TrainingStage(
        train_images=arguments.train_images,
        train_labels=arguments.train_labels,
        validation_images=arguments.validation_images,
        validation_labels=arguments.validation_labels,
        params_path=arguments.params_path,
        model_output=arguments.model_output,
        history_output=arguments.history_output,
        plot_output=arguments.plot_output,
        documentation_figures_directory=arguments.documentation_figures_directory,
    )
    stage.run()
