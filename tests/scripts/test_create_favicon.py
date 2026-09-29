"""Tests for the favicon creation utility."""

from pathlib import Path

import pytest
from PIL import Image, UnidentifiedImageError
from PIL.IcoImagePlugin import IcoImageFile

from scripts.create_favicon import DEFAULT_SIZES, create_favicon, main


def _create_source_image(
    path: Path,
    size: tuple[int, int] = (40, 20),
) -> None:
    """Create a synthetic, non-square image for a test."""
    image = Image.new("RGBA", size, color=(30, 100, 180, 255))
    image.save(path, format="PNG")


def _favicon_sizes(path: Path) -> set[tuple[int, int]]:
    """Return all image dimensions stored in an ICO file."""
    with Image.open(path) as image:
        assert isinstance(image, IcoImageFile)
        return image.ico.sizes()


def test_create_favicon_writes_all_default_sizes(tmp_path: Path) -> None:
    """The default ICO should contain every advertised resolution."""
    input_path = tmp_path / "source.png"
    output_path = tmp_path / "favicon.ico"
    _create_source_image(input_path)

    create_favicon(input_path, output_path)

    assert output_path.is_file()
    assert _favicon_sizes(output_path) == {(size, size) for size in DEFAULT_SIZES}


def test_create_favicon_centres_image_without_changing_aspect_ratio(
    tmp_path: Path,
) -> None:
    """A non-square source should be centred on a transparent square canvas."""
    input_path = tmp_path / "source.png"
    output_path = tmp_path / "favicon.ico"
    _create_source_image(input_path, size=(40, 20))

    create_favicon(input_path, output_path, sizes=(48,))

    with Image.open(output_path) as image:
        assert isinstance(image, IcoImageFile)
        icon = image.ico.getimage((48, 48)).convert("RGBA")

    alpha_channel = icon.getchannel("A")
    assert alpha_channel.getbbox() == (0, 12, 48, 36)


def test_create_favicon_sorts_and_deduplicates_custom_sizes(tmp_path: Path) -> None:
    """Repeated, unordered dimensions should create one frame per size."""
    input_path = tmp_path / "source.png"
    output_path = tmp_path / "favicon.ico"
    _create_source_image(input_path)

    create_favicon(input_path, output_path, sizes=(48, 16, 32, 16))

    assert _favicon_sizes(output_path) == {(16, 16), (32, 32), (48, 48)}


@pytest.mark.parametrize("sizes", [(), (0,), (257,), (16, -1)])
def test_create_favicon_rejects_invalid_sizes(
    tmp_path: Path,
    sizes: tuple[int, ...],
) -> None:
    """ICO dimensions must be present and fall within the supported range."""
    input_path = tmp_path / "source.png"
    _create_source_image(input_path)

    with pytest.raises(ValueError, match="favicon size|Favicon sizes"):
        create_favicon(input_path, tmp_path / "favicon.ico", sizes=sizes)


def test_create_favicon_rejects_missing_input(tmp_path: Path) -> None:
    """A missing source should produce a clear file error."""
    with pytest.raises(FileNotFoundError, match="Input image does not exist"):
        create_favicon(tmp_path / "missing.png", tmp_path / "favicon.ico")


def test_create_favicon_rejects_missing_output_directory(tmp_path: Path) -> None:
    """The utility should not silently create a misspelled output directory."""
    input_path = tmp_path / "source.png"
    _create_source_image(input_path)

    with pytest.raises(FileNotFoundError, match="Output directory does not exist"):
        create_favicon(input_path, tmp_path / "missing" / "favicon.ico")


def test_create_favicon_rejects_same_input_and_output_path(tmp_path: Path) -> None:
    """The source image should never be overwritten in place."""
    input_path = tmp_path / "source.png"
    _create_source_image(input_path)

    with pytest.raises(ValueError, match="must be different"):
        create_favicon(input_path, input_path)


def test_create_favicon_rejects_unrecognised_image(tmp_path: Path) -> None:
    """An existing non-image file should be rejected by Pillow."""
    input_path = tmp_path / "not-an-image.txt"
    input_path.write_text("not an image", encoding="utf-8")

    with pytest.raises(UnidentifiedImageError):
        create_favicon(input_path, tmp_path / "favicon.ico")


def test_main_creates_favicon_with_custom_sizes(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The CLI entry point should accept comma-separated custom sizes."""
    input_path = tmp_path / "source.png"
    output_path = tmp_path / "favicon.ico"
    _create_source_image(input_path)

    exit_code = main(
        ["--sizes", "16,32", str(input_path), str(output_path)],
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.out == f"Created favicon: {output_path}\n"
    assert captured.err == ""
    assert _favicon_sizes(output_path) == {(16, 16), (32, 32)}


def test_main_reports_failure_to_standard_error(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The CLI entry point should return a failure status for invalid input."""
    input_path = tmp_path / "missing.png"
    output_path = tmp_path / "favicon.ico"

    exit_code = main([str(input_path), str(output_path)])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert captured.out == ""
    assert captured.err == f"Error: Input image does not exist: {input_path}\n"
