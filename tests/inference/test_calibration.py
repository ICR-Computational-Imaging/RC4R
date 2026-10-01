"""Tests for reusable probability calibration."""

from pathlib import Path

import numpy as np
import pytest

from dermapred.inference.calibration import ProbabilityCalibrator


@pytest.mark.parametrize("method", ["isotonic", "platt"])
def test_probability_calibrator_fits_predicts_and_round_trips(
    tmp_path: Path,
    method: str,
) -> None:
    """Both supported methods should survive transparent JSON storage."""
    logits = np.array([-3.0, -2.0, -1.0, 0.0, 1.0, 2.0, 3.0, 4.0])
    labels = np.array([0, 0, 0, 1, 0, 1, 1, 1])

    calibrator = ProbabilityCalibrator.fit(logits, labels, method)
    expected = calibrator.predict_proba(logits)
    output_path = tmp_path / "calibrator.json"
    calibrator.save(output_path)
    restored = ProbabilityCalibrator.load(output_path)

    assert restored.method == method
    np.testing.assert_allclose(restored.predict_proba(logits), expected)
    assert np.all((expected >= 0) & (expected <= 1))


def test_probability_calibrator_rejects_unknown_method() -> None:
    """Unsupported calibration methods should fail explicitly."""
    with pytest.raises(ValueError, match="Calibration method"):
        ProbabilityCalibrator.fit(
            np.array([-1.0, 1.0]),
            np.array([0, 1]),
            "isomap",
        )
