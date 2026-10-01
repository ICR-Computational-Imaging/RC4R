"""DVC stage for calibrating DermaPred validation probabilities."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path

import numpy as np
import torch
import yaml
from sklearn.metrics import brier_score_loss
from sklearn.model_selection import StratifiedKFold

from dermapred.inference.calibration import (
    CALIBRATION_METHODS,
    ProbabilityCalibrator,
    expected_calibration_error,
    logits_to_probabilities,
)
from dermapred.models.binary_classifier import LeNetBinary
from dermapred.plotting.calibration import plot_calibration_curves


class CalibrationParameters:
    """Validated settings for cross-validated probability calibration."""

    def __init__(
        self,
        method: str,
        cross_validation_folds: int,
        reliability_bins: int,
        inference_batch_size: int,
        random_seed: int,
    ) -> None:
        """Store and validate calibration settings.

        Args:
            method: Calibration method, either ``isotonic`` or ``platt``.
            cross_validation_folds: Number of stratified validation folds.
            reliability_bins: Number of bins in the reliability diagram.
            inference_batch_size: Images processed in each inference batch.
            random_seed: Seed used to construct validation folds.

        Returns:
            None.

        Raises:
            ValueError: If a method or numerical setting is invalid.
        """
        if method not in CALIBRATION_METHODS:
            raise ValueError(f"Calibration method must be one of {CALIBRATION_METHODS}.")
        if cross_validation_folds < 2:
            raise ValueError("cross_validation_folds must be at least two.")
        if reliability_bins <= 0 or inference_batch_size <= 0 or random_seed < 0:
            raise ValueError("Bins and batch size must be positive; seed must be non-negative.")
        self.method = method
        self.cross_validation_folds = cross_validation_folds
        self.reliability_bins = reliability_bins
        self.inference_batch_size = inference_batch_size
        self.random_seed = random_seed


def load_calibration_parameters(params_path: Path) -> CalibrationParameters:
    """Load calibration settings from the project parameters file.

    Args:
        params_path: YAML file containing the ``calibration`` section.

    Returns:
        Validated calibration parameters.

    Raises:
        OSError: If the file cannot be read.
        TypeError: If a parameter has an incompatible type.
        ValueError: If required settings are missing or invalid.
    """
    try:
        parameters = yaml.safe_load(params_path.read_text(encoding="utf-8"))["calibration"]
        return CalibrationParameters(
            method=str(parameters["method"]),
            cross_validation_folds=int(parameters["cross_validation_folds"]),
            reliability_bins=int(parameters["reliability_bins"]),
            inference_batch_size=int(parameters["inference_batch_size"]),
            random_seed=int(parameters["random_seed"]),
        )
    except (KeyError, TypeError, yaml.YAMLError) as error:
        raise ValueError(f"Invalid calibration configuration in {params_path}.") from error


def predict_logits(
    model: LeNetBinary,
    images: np.ndarray,
    batch_size: int,
) -> np.ndarray:
    """Run deterministic batched inference over model-ready images.

    Args:
        model: Trained binary classifier in any current PyTorch mode.
        images: Model-ready array with shape ``(N, C, H, W)``.
        batch_size: Maximum number of images processed together.

    Returns:
        One-dimensional NumPy array containing one logit per image.

    Raises:
        RuntimeError: If the model cannot process an image batch.
        ValueError: If the image array or batch size is invalid.
    """
    if images.ndim != 4 or images.shape[0] == 0:
        raise ValueError("Calibration images must have shape (N, C, H, W).")
    if batch_size <= 0:
        raise ValueError("batch_size must be positive.")
    model.eval()
    predictions: list[np.ndarray] = []
    with torch.no_grad():
        for start in range(0, images.shape[0], batch_size):
            batch = torch.from_numpy(images[start : start + batch_size]).to(torch.float32)
            predictions.append(model(batch).detach().cpu().numpy().reshape(-1))
    return np.concatenate(predictions).astype(np.float64, copy=False)


def cross_validated_probabilities(
    logits: np.ndarray,
    labels: np.ndarray,
    parameters: CalibrationParameters,
) -> np.ndarray:
    """Generate out-of-fold calibrated validation probabilities.

    Args:
        logits: Validation logits from the trained classifier.
        labels: Aligned binary validation labels.
        parameters: Calibration method, fold count, and random seed.

    Returns:
        Calibrated probability for each validation sample from a calibrator
        that was not fitted on that sample.

    Raises:
        ValueError: If folds cannot be stratified or inputs are invalid.
    """
    labels = np.asarray(labels).reshape(-1)
    class_counts = np.bincount(labels.astype(int), minlength=2)
    if class_counts.min() < parameters.cross_validation_folds:
        raise ValueError("Each class must contain at least one sample per calibration fold.")
    splitter = StratifiedKFold(
        n_splits=parameters.cross_validation_folds,
        shuffle=True,
        random_state=parameters.random_seed,
    )
    calibrated = np.empty(labels.shape[0], dtype=np.float64)
    for fit_indices, held_out_indices in splitter.split(logits, labels):
        fold_calibrator = ProbabilityCalibrator.fit(
            logits[fit_indices], labels[fit_indices], parameters.method
        )
        calibrated[held_out_indices] = fold_calibrator.predict_proba(logits[held_out_indices])
    return calibrated


class CalibrationStage:
    """Fit, assess, and save validation-based probability calibration."""

    def __init__(
        self,
        model_path: Path,
        validation_images: Path,
        validation_labels: Path,
        params_path: Path,
        calibrator_output: Path,
        metrics_output: Path,
        plot_output: Path,
    ) -> None:
        """Configure calibration inputs and outputs.

        Args:
            model_path: Trained classifier checkpoint.
            validation_images: Processed validation-image array.
            validation_labels: Binary validation-label array.
            params_path: YAML file containing calibration settings.
            calibrator_output: Destination for the fitted JSON mapping.
            metrics_output: Destination for validation calibration metrics.
            plot_output: Destination for the reliability diagram.

        Returns:
            None.

        Raises:
            TypeError: If any path is not a ``pathlib.Path`` object.
        """
        paths = (
            model_path,
            validation_images,
            validation_labels,
            params_path,
            calibrator_output,
            metrics_output,
            plot_output,
        )
        if not all(isinstance(path, Path) for path in paths):
            raise TypeError("Calibration stage paths must be pathlib.Path objects.")
        self.model_path = model_path
        self.validation_images = validation_images
        self.validation_labels = validation_labels
        self.params_path = params_path
        self.calibrator_output = calibrator_output
        self.metrics_output = metrics_output
        self.plot_output = plot_output

    def run(self) -> None:
        """Generate validation calibration evidence and a final calibrator.

        Returns:
            None.

        Raises:
            OSError: If an input cannot be read or an output cannot be written.
            RuntimeError: If the checkpoint or model inference fails.
            TypeError: If a checkpoint or configuration value has the wrong type.
            ValueError: If inputs, settings, labels, or fitted values are invalid.
        """
        parameters = load_calibration_parameters(self.params_path)
        checkpoint = torch.load(self.model_path, map_location="cpu", weights_only=True)
        model = LeNetBinary(input_channels=int(checkpoint["input_channels"]))
        model.load_state_dict(checkpoint["model_state_dict"])

        images = np.load(self.validation_images, allow_pickle=False)
        labels = np.load(self.validation_labels, allow_pickle=False).reshape(-1)
        if images.shape[0] != labels.shape[0] or set(np.unique(labels).tolist()) != {0, 1}:
            raise ValueError("Validation images and binary labels must be aligned.")
        logits = predict_logits(model, images, parameters.inference_batch_size)
        raw_probabilities = logits_to_probabilities(logits)
        calibrated_probabilities = cross_validated_probabilities(logits, labels, parameters)

        final_calibrator = ProbabilityCalibrator.fit(logits, labels, parameters.method)
        final_calibrator.save(self.calibrator_output)

        metrics = {
            "method": parameters.method,
            "cross_validation_folds": parameters.cross_validation_folds,
            "brier_score_before": float(brier_score_loss(labels, raw_probabilities)),
            "brier_score_after": float(brier_score_loss(labels, calibrated_probabilities)),
            "expected_calibration_error_before": expected_calibration_error(
                labels, raw_probabilities, parameters.reliability_bins
            ),
            "expected_calibration_error_after": expected_calibration_error(
                labels, calibrated_probabilities, parameters.reliability_bins
            ),
        }
        self.metrics_output.parent.mkdir(parents=True, exist_ok=True)
        self.metrics_output.write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
        plot_calibration_curves(
            labels,
            raw_probabilities,
            calibrated_probabilities,
            self.plot_output,
            parameters.reliability_bins,
        )


def _parse_args(arguments: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments for the calibration stage.

    Args:
        arguments: Optional command-line arguments. When omitted, arguments
            are read from ``sys.argv``.

    Returns:
        Parsed paths for calibration inputs and outputs.

    Raises:
        SystemExit: If a required argument is missing or invalid.
    """
    parser = argparse.ArgumentParser(description="Calibrate DermaPred probabilities.")
    for option in (
        "model-path",
        "validation-images",
        "validation-labels",
        "params-path",
        "calibrator-output",
        "metrics-output",
        "plot-output",
    ):
        parser.add_argument(f"--{option}", type=Path, required=True)
    return parser.parse_args(arguments)


if __name__ == "__main__":
    arguments = _parse_args()
    stage = CalibrationStage(
        model_path=arguments.model_path,
        validation_images=arguments.validation_images,
        validation_labels=arguments.validation_labels,
        params_path=arguments.params_path,
        calibrator_output=arguments.calibrator_output,
        metrics_output=arguments.metrics_output,
        plot_output=arguments.plot_output,
    )
    stage.run()
