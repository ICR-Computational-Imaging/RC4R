"""Tests for reusable DermaPred image preprocessing."""

import numpy as np
import pytest

from dermapred.data.preprocessing import (
    channels_first,
    preprocess_images,
    scale_images,
    validate_images,
)


def test_scale_images_maps_full_uint8_range() -> None:
    """Pixel endpoints should map exactly to the requested floating range."""
    images = np.array([[[[0, 128, 255]]]], dtype=np.uint8)

    scaled = scale_images(images)

    assert scaled.dtype == np.float32
    np.testing.assert_allclose(
        scaled,
        np.array([[[[-1.0, 1.0 / 255.0, 1.0]]]], dtype=np.float32),
        atol=1e-7,
    )


def test_channels_first_transposes_and_makes_contiguous() -> None:
    """Channel-last arrays should become contiguous PyTorch-style arrays."""
    images = np.arange(24, dtype=np.float32).reshape(1, 2, 4, 3)

    transformed = channels_first(images)

    assert transformed.shape == (1, 3, 2, 4)
    assert transformed.flags.c_contiguous
    np.testing.assert_array_equal(transformed[:, 0], images[:, :, :, 0])


def test_preprocess_images_returns_model_ready_batch() -> None:
    """The combined operation should scale and transpose the image batch."""
    images = np.zeros((2, 3, 4, 3), dtype=np.uint8)

    processed = preprocess_images(images)

    assert processed.shape == (2, 3, 3, 4)
    assert processed.dtype == np.float32
    assert np.all(processed == -1.0)


@pytest.mark.parametrize(
    ("images", "error", "message"),
    [
        (np.zeros((2, 28, 28)), ValueError, "shape"),
        (np.empty((0, 28, 28, 3)), ValueError, "at least one"),
        (np.full((1, 1, 1, 3), np.nan), ValueError, "finite"),
        (np.full((1, 1, 1, 3), 256), ValueError, "range"),
        (np.zeros((1, 1, 1, 3), dtype=bool), TypeError, "numeric"),
    ],
)
def test_validate_images_rejects_invalid_arrays(
    images: np.ndarray,
    error: type[Exception],
    message: str,
) -> None:
    """Invalid shapes, values, and data types should fail clearly."""
    with pytest.raises(error, match=message):
        validate_images(images)
