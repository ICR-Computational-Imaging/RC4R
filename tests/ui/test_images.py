"""Crop real synthetic pixel arrays without involving a model or Qt."""

import numpy as np
import pytest
from PIL import Image

from dermapred.ui.images import load_example_image, load_image, selection_bounds, square_crop


def test_example_is_an_installed_resource_independent_of_working_directory(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    image = load_example_image()
    assert image.mode == "RGB"
    assert image.width > 0 and image.height > 0
    assert len(image.tobytes()) == image.width * image.height * 3


@pytest.mark.parametrize(
    ("coordinates", "expected"),
    [((1.2, 2.4, 8.1, 9.2), (1, 2, 9, 10)),
     ((8.1, 9.2, 1.2, 2.4), (1, 2, 9, 10)),
     ((-4, -8, 40, 50), (0, 0, 12, 10))],
)
def test_selection_maps_to_original_pixels(coordinates, expected):
    assert selection_bounds(coordinates, (12, 10)) == expected


@pytest.mark.parametrize(
    "coordinates", [(1, 1, 1, 5), (1, 1, 5, 1), (20, 20, 30, 30), (float("nan"), 0, 4, 4)]
)
def test_reject_invalid_selection(coordinates):
    with pytest.raises(ValueError):
        selection_bounds(coordinates, (12, 10))


@pytest.mark.parametrize("bounds", [(1, 2, 11, 6), (2, 0, 6, 10)])
def test_square_crop_keeps_centre_pixels(bounds):
    pixels = np.arange(12 * 10 * 3, dtype=np.uint8).reshape(10, 12, 3)
    crop = square_crop(Image.fromarray(pixels), bounds)
    left, top, right, bottom = bounds
    side = min(right - left, bottom - top)
    x = left + (right - left - side) // 2
    y = top + (bottom - top - side) // 2
    assert crop.size == (side, side)
    np.testing.assert_array_equal(np.asarray(crop), pixels[y:y + side, x:x + side])


def test_crop_rejects_out_of_bounds():
    with pytest.raises(ValueError):
        square_crop(Image.new("RGB", (10, 10)), (-1, 0, 5, 5))


@pytest.mark.parametrize("suffix", ["jpg", "tiff", "png", "bmp"])
def test_load_supported_images_detaches_pixels(tmp_path, suffix):
    path = tmp_path / f"image.{suffix}"
    Image.new("RGB", (30, 20), "red").save(path)
    image = load_image(path)
    path.unlink()
    assert image.size == (30, 20)
    assert image.mode == "RGB"
    assert image.getpixel((0, 0))[0] > 240


def test_load_applies_exif_orientation(tmp_path):
    path = tmp_path / "rotated.jpg"
    image = Image.new("RGB", (30, 20))
    exif = image.getexif()
    exif[274] = 6
    image.save(path, exif=exif)
    assert load_image(path).size == (20, 30)
