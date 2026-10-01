"""Reusable image preprocessing for the DermaPred example."""

from __future__ import annotations

import numpy as np


def validate_images(images: np.ndarray) -> None:
    """Validate a batch of channel-last RGB images.

    Args:
        images: Image batch expected to have shape ``(N, H, W, 3)`` and pixel
            values in the inclusive range ``[0, 255]``.

    Returns:
        None. Successful completion indicates that the image batch is valid.

    Raises:
        TypeError: If the array does not have a numeric data type.
        ValueError: If the shape or pixel values are invalid.
    """
    if images.ndim != 4 or images.shape[-1] != 3:
        raise ValueError(f"Images must have shape (N, H, W, 3); received {images.shape}.")
    if images.shape[0] == 0:
        raise ValueError("Images must contain at least one sample.")
    if not np.issubdtype(images.dtype, np.number) or np.issubdtype(images.dtype, np.bool_):
        raise TypeError("Images must have a numeric data type.")
    if not np.isfinite(images).all():
        raise ValueError("Images must contain only finite pixel values.")
    if images.min() < 0 or images.max() > 255:
        raise ValueError("Image pixel values must be in the range [0, 255].")


def scale_images(images: np.ndarray) -> np.ndarray:
    """Convert image pixels to ``float32`` and scale them to ``[-1, 1]``.

    Args:
        images: Channel-last RGB image batch with shape ``(N, H, W, 3)`` and
            pixel values in the inclusive range ``[0, 255]``.

    Returns:
        A ``float32`` array with the same shape as ``images`` and values in
        the inclusive range ``[-1, 1]``.

    Raises:
        TypeError: If the array does not have a numeric data type.
        ValueError: If the shape or pixel values are invalid.
    """
    validate_images(images)
    float_images = images.astype(np.float32, copy=False)
    return float_images / np.float32(127.5) - np.float32(1.0)


def channels_first(images: np.ndarray) -> np.ndarray:
    """Transpose an image batch from ``NHWC`` to contiguous ``NCHW`` format.

    Args:
        images: Channel-last RGB image batch with shape ``(N, H, W, 3)``.

    Returns:
        A C-contiguous array with shape ``(N, 3, H, W)`` and the same data
        type and pixel values as ``images``.

    Raises:
        ValueError: If ``images`` is not a four-dimensional, channel-last RGB
            array.
    """
    if images.ndim != 4 or images.shape[-1] != 3:
        raise ValueError(f"Images must have shape (N, H, W, 3); received {images.shape}.")
    return np.ascontiguousarray(np.transpose(images, (0, 3, 1, 2)))


def preprocess_images(images: np.ndarray) -> np.ndarray:
    """Validate, scale, and convert a batch of images for PyTorch models.

    Args:
        images: Channel-last RGB image batch with shape ``(N, H, W, 3)`` and
            pixel values in the inclusive range ``[0, 255]``.

    Returns:
        A C-contiguous ``float32`` array with shape ``(N, 3, H, W)`` and
        pixel values in the inclusive range ``[-1, 1]``.

    Raises:
        TypeError: If the array does not have a numeric data type.
        ValueError: If the shape or pixel values are invalid.
    """
    return channels_first(scale_images(images))
