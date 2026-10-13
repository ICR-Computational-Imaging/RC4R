"""DVC stage for final evaluation on the untouched DermaMNIST test split."""

from __future__ import annotations

import argparse
import csv
import shutil
from collections.abc import Sequence
from pathlib import Path

import numpy as np
import torch
import yaml
from sklearn.metrics import confusion_matrix

from dermapred.evaluation.metrics import (
    bootstrap_metric_intervals,
    calculate_binary_metrics,
    predict_logits,
    stratified_bootstrap_indices,
)
from dermapred.inference.calibration import ProbabilityCalibrator, logits_to_probabilities
from dermapred.models.binary_classifier import LeNetBinary
from dermapred.plotting.evaluation import (
    plot_calibration_curve,
    plot_confusion_matrix,
    plot_roc_curve,
)


class EvaluationParameters:
    """Validated parameters for final test-set evaluation."""

    def __init__(
        self,
        threshold: float,
        bootstrap_iterations: int,
        confidence_level: float,
        reliability_bins: int,
        inference_batch_size: int,
        random_seed: int,
    ) -> None:
        """Store and validate evaluation settings.

        Args:
            threshold: Fixed positive-classification threshold.
            bootstrap_iterations: Number of stratified resamples.
            confidence_level: Width of central bootstrap intervals.
            reliability_bins: Equal-width bins in calibration calculations.
            inference_batch_size: Images processed in each inference batch.
            random_seed: Seed used for bootstrap sampling.

        Returns:
            None.

        Raises:
            ValueError: If a parameter falls outside its valid range.
        """
        if not 0 <= threshold <= 1:
            raise ValueError("threshold must be between zero and one.")
        if bootstrap_iterations <= 0 or reliability_bins <= 0 or inference_batch_size <= 0:
            raise ValueError("Iterations, bins, and batch size must be positive.")
        if not 0 < confidence_level < 1 or random_seed < 0:
            raise ValueError("Confidence level and random seed are invalid.")
        self.threshold = threshold
        self.bootstrap_iterations = bootstrap_iterations
        self.confidence_level = confidence_level
        self.reliability_bins = reliability_bins
        self.inference_batch_size = inference_batch_size
        self.random_seed = random_seed


def load_evaluation_parameters(params_path: Path) -> EvaluationParameters:
    """Load final evaluation settings from a YAML parameters file.

    Args:
        params_path: YAML file containing the ``evaluation`` section.

    Returns:
        Validated evaluation settings.

    Raises:
        OSError: If the parameters file cannot be read.
        TypeError: If a parameter has an incompatible type.
        ValueError: If required settings are missing or invalid.
    """
    try:
        parameters = yaml.safe_load(params_path.read_text(encoding="utf-8"))["evaluation"]
        return EvaluationParameters(
            threshold=float(parameters["threshold"]),
            bootstrap_iterations=int(parameters["bootstrap_iterations"]),
            confidence_level=float(parameters["confidence_level"]),
            reliability_bins=int(parameters["reliability_bins"]),
            inference_batch_size=int(parameters["inference_batch_size"]),
            random_seed=int(parameters["random_seed"]),
        )
    except (KeyError, TypeError, yaml.YAMLError) as error:
        raise ValueError(f"Invalid evaluation configuration in {params_path}.") from error


class EvaluationStage:
    """Evaluate the frozen model and calibrator once on the test split."""

    def __init__(
        self,
        model_path: Path,
        calibrator_path: Path,
        test_images: Path,
        test_labels: Path,
        params_path: Path,
        predictions_output: Path,
        metrics_output: Path,
        confusion_matrix_output: Path,
        roc_curve_output: Path,
        calibration_curve_output: Path,
        documentation_figures_directory: Path | None = None,
    ) -> None:
        """Configure final evaluation inputs and outputs.

        Args:
            model_path: Trained binary-classifier checkpoint.
            calibrator_path: Validation-fitted calibration mapping.
            test_images: Processed test-image array.
            test_labels: Binary test-label array.
            params_path: YAML file containing evaluation settings.
            predictions_output: Destination for sample-level predictions.
            metrics_output: Destination for summary metrics and intervals.
            confusion_matrix_output: Destination confusion-matrix PNG.
            roc_curve_output: Destination ROC-curve PNG.
            calibration_curve_output: Destination reliability-diagram PNG.
            documentation_figures_directory: Optional MkDocs assets directory
                that receives copies of the generated figures and metrics CSV.

        Returns:
            None.

        Raises:
            TypeError: If any path is not a ``pathlib.Path`` object.
        """
        paths = (
            model_path,
            calibrator_path,
            test_images,
            test_labels,
            params_path,
            predictions_output,
            metrics_output,
            confusion_matrix_output,
            roc_curve_output,
            calibration_curve_output,
        )
        if not all(isinstance(path, Path) for path in paths):
            raise TypeError("Evaluation stage paths must be pathlib.Path objects.")
        self.model_path = model_path
        self.calibrator_path = calibrator_path
        self.test_images = test_images
        self.test_labels = test_labels
        self.params_path = params_path
        self.predictions_output = predictions_output
        self.metrics_output = metrics_output
        self.confusion_matrix_output = confusion_matrix_output
        self.roc_curve_output = roc_curve_output
        self.calibration_curve_output = calibration_curve_output
        self.documentation_figures_directory = documentation_figures_directory

    def run(self) -> None:
        """Generate final test predictions, metrics, and review figures.

        Returns:
            None.

        Raises:
            OSError: If an input cannot be read or an output cannot be written.
            RuntimeError: If checkpoint loading or model inference fails.
            TypeError: If stored objects contain incompatible types.
            ValueError: If test data, parameters, or predictions are invalid.
        """
        parameters = load_evaluation_parameters(self.params_path)
        checkpoint = torch.load(self.model_path, map_location="cpu", weights_only=True)
        model = LeNetBinary(input_channels=int(checkpoint["input_channels"]))
        model.load_state_dict(checkpoint["model_state_dict"])
        calibrator = ProbabilityCalibrator.load(self.calibrator_path)

        images = np.load(self.test_images, allow_pickle=False)
        labels = np.load(self.test_labels, allow_pickle=False).reshape(-1)
        if images.shape[0] != labels.shape[0] or set(np.unique(labels).tolist()) != {0, 1}:
            raise ValueError("Test images and binary labels must be aligned.")
        logits = predict_logits(model, images, parameters.inference_batch_size)
        raw_probabilities = logits_to_probabilities(logits)
        calibrated_probabilities = calibrator.predict_proba(logits)
        predictions = (calibrated_probabilities >= parameters.threshold).astype(np.uint8)

        bootstrap_indices = stratified_bootstrap_indices(
            labels, parameters.bootstrap_iterations, parameters.random_seed
        )
        metrics = calculate_binary_metrics(
            labels,
            calibrated_probabilities,
            parameters.threshold,
            parameters.reliability_bins,
        )
        intervals = bootstrap_metric_intervals(
            labels,
            calibrated_probabilities,
            bootstrap_indices,
            parameters.threshold,
            parameters.reliability_bins,
            parameters.confidence_level,
        )
        raw_metrics = calculate_binary_metrics(
            labels,
            raw_probabilities,
            parameters.threshold,
            parameters.reliability_bins,
        )

        self.predictions_output.parent.mkdir(parents=True, exist_ok=True)
        with self.predictions_output.open("w", encoding="utf-8", newline="") as output_file:
            writer = csv.writer(output_file)
            writer.writerow(
                ["sample", "label", "raw_probability", "calibrated_probability", "prediction"]
            )
            writer.writerows(
                zip(
                    range(labels.size),
                    labels,
                    raw_probabilities,
                    calibrated_probabilities,
                    predictions,
                    strict=True,
                )
            )

        matrix = confusion_matrix(labels, predictions, labels=[0, 1])
        true_negative, false_positive, false_negative, true_positive = matrix.ravel()
        metadata: dict[str, str | int | float] = {
            "sample_count": labels.size,
            "positive_count": int(labels.sum()),
            "negative_count": int(labels.size - labels.sum()),
            "prevalence": float(labels.mean()),
            "threshold": parameters.threshold,
            "true_positive": int(true_positive),
            "false_positive": int(false_positive),
            "true_negative": int(true_negative),
            "false_negative": int(false_negative),
            "bootstrap_iterations": parameters.bootstrap_iterations,
            "confidence_level": parameters.confidence_level,
            "calibration_method": calibrator.method,
            "raw_brier_score": raw_metrics["brier_score"],
            "raw_expected_calibration_error": raw_metrics[
                "expected_calibration_error"
            ],
        }
        self.metrics_output.parent.mkdir(parents=True, exist_ok=True)
        with self.metrics_output.open("w", encoding="utf-8", newline="") as output_file:
            writer = csv.writer(output_file)
            writer.writerow(["metric", "value", "ci_lower", "ci_upper"])
            for name, value in metrics.items():
                lower, upper = intervals[name]
                writer.writerow([name, value, lower, upper])
            for name, value in metadata.items():
                writer.writerow([name, value, "", ""])

        plot_confusion_matrix(
            labels, calibrated_probabilities, parameters.threshold, self.confusion_matrix_output
        )
        plot_roc_curve(
            labels,
            calibrated_probabilities,
            bootstrap_indices,
            parameters.confidence_level,
            self.roc_curve_output,
        )
        plot_calibration_curve(
            labels,
            raw_probabilities,
            calibrated_probabilities,
            bootstrap_indices,
            parameters.reliability_bins,
            parameters.confidence_level,
            self.calibration_curve_output,
        )
        if self.documentation_figures_directory is not None:
            self.documentation_figures_directory.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(
                self.metrics_output,
                self.documentation_figures_directory / self.metrics_output.name,
            )
            for figure_path in (
                self.confusion_matrix_output,
                self.roc_curve_output,
                self.calibration_curve_output,
            ):
                shutil.copyfile(
                    figure_path,
                    self.documentation_figures_directory / figure_path.name,
                )


def _parse_args(arguments: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments for final test evaluation.

    Args:
        arguments: Optional command-line arguments. When omitted, arguments
            are read from ``sys.argv``.

    Returns:
        Parsed paths for every evaluation input and output.

    Raises:
        SystemExit: If a required argument is missing or invalid.
    """
    parser = argparse.ArgumentParser(description="Evaluate DermaPred on the test split.")
    for option in (
        "model-path",
        "calibrator-path",
        "test-images",
        "test-labels",
        "params-path",
        "predictions-output",
        "metrics-output",
        "confusion-matrix-output",
        "roc-curve-output",
        "calibration-curve-output",
    ):
        parser.add_argument(f"--{option}", type=Path, required=True)
    parser.add_argument("--documentation-figures-directory", type=Path)
    return parser.parse_args(arguments)


if __name__ == "__main__":
    arguments = _parse_args()
    stage = EvaluationStage(
        model_path=arguments.model_path,
        calibrator_path=arguments.calibrator_path,
        test_images=arguments.test_images,
        test_labels=arguments.test_labels,
        params_path=arguments.params_path,
        predictions_output=arguments.predictions_output,
        metrics_output=arguments.metrics_output,
        confusion_matrix_output=arguments.confusion_matrix_output,
        roc_curve_output=arguments.roc_curve_output,
        calibration_curve_output=arguments.calibration_curve_output,
        documentation_figures_directory=arguments.documentation_figures_directory,
    )
    stage.run()
