"""Tests for the proof-of-concept binary classifier."""

import pytest
import torch

from dermapred.models.binary_classifier import LeNetBinary


def test_binary_classifier_returns_one_logit_per_image() -> None:
    """The model output should align with a batch of binary labels."""
    model = LeNetBinary()
    images = torch.zeros((4, 3, 28, 28), dtype=torch.float32)

    logits = model(images)

    assert logits.shape == (4, 1)


def test_binary_classifier_converts_logits_to_probabilities() -> None:
    """The inference helper should return bounded probabilities."""
    model = LeNetBinary()
    images = torch.zeros((4, 3, 28, 28), dtype=torch.float32)

    probabilities = model.predict_proba(images)

    assert probabilities.shape == (4, 1)
    assert torch.all((probabilities >= 0) & (probabilities <= 1))


@pytest.mark.parametrize("input_channels", [0, -1, 3.0, True])
def test_binary_classifier_rejects_invalid_channel_count(
    input_channels: object,
) -> None:
    """Invalid constructor configuration should fail clearly."""
    with pytest.raises(ValueError, match="positive integer"):
        LeNetBinary(input_channels=input_channels)  # type: ignore[arg-type]
