"""Original-image coordinates and square crops for the inference interface."""

from __future__ import annotations

import math
from importlib.resources import files
from pathlib import Path

from PIL import Image, ImageOps


def load_image(path: Path) -> Image.Image:
    """Decode the first frame, apply EXIF orientation, and detach RGB pixels."""
    with Image.open(path) as image:
        return ImageOps.exif_transpose(image).convert("RGB")


def load_example_image() -> Image.Image:
    """Read the installed example resource without depending on a source checkout."""
    example = files("dermapred").joinpath("examples", "example_image.jpg")
    with example.open("rb") as stream:
        with Image.open(stream) as image:
            return ImageOps.exif_transpose(image).convert("RGB")


def selection_bounds(
    coordinates: tuple[float, float, float, float], size: tuple[int, int]
) -> tuple[int, int, int, int]:
    """Convert a drag in either direction into clipped Pillow crop bounds.

    Coordinates are (start x, start y, end x, end y), in original image pixels.
    Lower edges round down and upper edges round up to include selected pixels.
    """
    if not all(math.isfinite(value) for value in coordinates):
        raise ValueError("Selection coordinates must be finite.")
    x0, y0, x1, y1 = coordinates
    if x0 == x1 or y0 == y1:
        raise ValueError("Draw a bounding box with non-zero width and height.")
    width, height = size
    left = max(0, min(width, math.floor(min(x0, x1))))
    right = max(0, min(width, math.ceil(max(x0, x1))))
    top = max(0, min(height, math.floor(min(y0, y1))))
    bottom = max(0, min(height, math.ceil(max(y0, y1))))
    if left >= right or top >= bottom:
        raise ValueError("The bounding box must overlap the image.")
    return left, top, right, bottom


def square_crop(image: Image.Image, bounds: tuple[int, int, int, int]) -> Image.Image:
    """Centre-crop the selected region's longer dimension, without resizing."""
    left, top, right, bottom = bounds
    width, height = image.size
    if not (0 <= left < right <= width and 0 <= top < bottom <= height):
        raise ValueError("The bounding box must be within the image.")
    side = min(right - left, bottom - top)
    left += (right - left - side) // 2
    top += (bottom - top - side) // 2
    return image.crop((left, top, left + side, top + side))
