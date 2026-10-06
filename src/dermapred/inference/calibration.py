"""Reusable probability calibration for DermaPred model inference."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

CALIBRATION_METHODS = ("isotonic", "platt")


def logits_to_probabilities(logits: np.ndarray) -> np.ndarray:
    """Convert model logits to probabilities using a stable sigmoid.

    Args:
        logits: One-dimensional array of unbounded model scores.

    Returns:
        Floating array of probabilities in the inclusive range ``[0, 1]``.

    Raises:
        ValueError: If ``logits`` is not one-dimensional or contains a
            non-finite value.
    """
    logits = np.asarray(logits, dtype=np.float64)
    if logits.ndim != 1 or not np.isfinite(logits).all():
        raise ValueError("Logits must be a one-dimensional finite array.")
    clipped_logits = np.clip(logits, -709.0, 709.0)
    return 1.0 / (1.0 + np.exp(-clipped_logits))


def expected_calibration_error(
    labels: np.ndarray,
    probabilities: np.ndarray,
    bins: int,
) -> float:
    """Calculate equally spaced expected calibration error.

    Args:
        labels: One-dimensional binary labels.
        probabilities: Aligned positive-class probabilities.
        bins: Number of equal-width bins between zero and one.

    Returns:
        Weighted absolute difference between confidence and observed frequency.

    Raises:
        ValueError: If arrays are misaligned, probabilities are invalid, or
            ``bins`` is not positive.
    """
    labels = np.asarray(labels).reshape(-1)
    probabilities = np.asarray(probabilities, dtype=np.float64).reshape(-1)
    if labels.shape != probabilities.shape or not labels.size:
        raise ValueError("Labels and probabilities must be non-empty and aligned.")
    if bins <= 0 or np.any((probabilities < 0) | (probabilities > 1)):
        raise ValueError("Bins must be positive and probabilities must be in [0, 1].")
    bin_indices = np.minimum((probabilities * bins).astype(int), bins - 1)
    error = 0.0
    for index in range(bins):
        mask = bin_indices == index
        if np.any(mask):
            error += float(mask.mean()) * abs(
                float(probabilities[mask].mean()) - float(labels[mask].mean())
            )
    return error


class ProbabilityCalibrator:
    """Apply a fitted isotonic or Platt calibration mapping to model logits."""

    def __init__(
        self,
        method: str,
        x_values: np.ndarray,
        y_values: np.ndarray,
    ) -> None:
        """Store a fitted calibration mapping.

        Args:
            method: Calibration method, either ``isotonic`` or ``platt``.
            x_values: Isotonic probability thresholds or the Platt coefficient.
            y_values: Isotonic calibrated thresholds or the Platt intercept.

        Returns:
            None.

        Raises:
            ValueError: If the method or fitted parameter arrays are invalid.
        """
        if method not in CALIBRATION_METHODS:
            raise ValueError(f"Calibration method must be one of {CALIBRATION_METHODS}.")
        x_values = np.asarray(x_values, dtype=np.float64)
        y_values = np.asarray(y_values, dtype=np.float64)
        if x_values.ndim != 1 or y_values.ndim != 1 or not x_values.size or not y_values.size:
            raise ValueError("Calibration parameters must be non-empty one-dimensional arrays.")
        if method == "isotonic" and x_values.shape != y_values.shape:
            raise ValueError("Isotonic threshold arrays must have matching shapes.")
        if method == "platt" and (x_values.size != 1 or y_values.size != 1):
            raise ValueError("Platt calibration requires one coefficient and one intercept.")
        self.method = method
        self.x_values = x_values
        self.y_values = y_values

    @classmethod
    def fit(
        cls,
        logits: np.ndarray,
        labels: np.ndarray,
        method: str,
    ) -> ProbabilityCalibrator:
        """Fit a probability calibrator from model logits and binary labels.

        Args:
            logits: One-dimensional array of unbounded model scores.
            labels: One-dimensional array of binary targets.
            method: Calibration method, either ``isotonic`` or ``platt``.

        Returns:
            Fitted calibrator that can be serialised or applied to new logits.

        Raises:
            ValueError: If the method, shapes, values, or label classes are
                invalid.
        """
        logits = np.asarray(logits, dtype=np.float64)
        labels = np.asarray(labels).reshape(-1)
        if logits.ndim != 1 or logits.shape[0] != labels.shape[0]:
            raise ValueError("Logits and labels must be aligned one-dimensional arrays.")
        if set(np.unique(labels).tolist()) != {0, 1}:
            raise ValueError("Calibration labels must contain both binary classes.")
        if method == "isotonic":
            from sklearn.isotonic import IsotonicRegression

            raw_probabilities = logits_to_probabilities(logits)
            estimator = IsotonicRegression(out_of_bounds="clip")
            estimator.fit(raw_probabilities, labels)
            return cls(
                method,
                np.asarray(estimator.X_thresholds_),
                np.asarray(estimator.y_thresholds_),
            )
        if method == "platt":
            from sklearn.linear_model import LogisticRegression

            estimator = LogisticRegression(C=np.inf, solver="lbfgs")
            estimator.fit(logits.reshape(-1, 1), labels)
            return cls(method, estimator.coef_.reshape(-1), estimator.intercept_.reshape(-1))
        raise ValueError(f"Calibration method must be one of {CALIBRATION_METHODS}.")

    def predict_proba(self, logits: np.ndarray) -> np.ndarray:
        """Apply the fitted mapping to model logits.

        Args:
            logits: One-dimensional array of unbounded model scores.

        Returns:
            One-dimensional array of calibrated positive-class probabilities.

        Raises:
            ValueError: If the logits are not one-dimensional and finite.
        """
        if self.method == "isotonic":
            probabilities = logits_to_probabilities(logits)
            return np.interp(probabilities, self.x_values, self.y_values)
        scaled_logits = self.x_values[0] * np.asarray(logits, dtype=np.float64) + self.y_values[0]
        return logits_to_probabilities(scaled_logits)

    def to_dict(self) -> dict[str, str | list[float]]:
        """Return a transparent JSON-compatible calibration representation.

        Returns:
            Dictionary containing the method and its fitted numerical mapping.

        Raises:
            ValueError: If a stored parameter cannot be converted to a finite
                floating-point value.
        """
        if not np.isfinite(self.x_values).all() or not np.isfinite(self.y_values).all():
            raise ValueError("Calibration parameters must be finite.")
        return {
            "method": self.method,
            "x_values": self.x_values.tolist(),
            "y_values": self.y_values.tolist(),
        }

    def save(self, output_path: Path) -> None:
        """Write the fitted calibration mapping as JSON.

        Args:
            output_path: Destination JSON file.

        Returns:
            None.

        Raises:
            OSError: If the destination cannot be created or written.
            ValueError: If a stored parameter is not finite.
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(self.to_dict(), indent=2) + "\n",
            encoding="utf-8",
        )

    @classmethod
    def load(cls, input_path: Path) -> ProbabilityCalibrator:
        """Restore a fitted calibration mapping from JSON.

        Args:
            input_path: Calibration JSON file.

        Returns:
            Restored calibrator ready to process model logits.

        Raises:
            KeyError: If a required JSON field is missing.
            OSError: If the file cannot be read.
            ValueError: If the JSON or calibration values are invalid.
        """
        parameters = json.loads(input_path.read_text(encoding="utf-8"))
        return cls(
            method=parameters["method"],
            x_values=np.asarray(parameters["x_values"], dtype=np.float64),
            y_values=np.asarray(parameters["y_values"], dtype=np.float64),
        )
