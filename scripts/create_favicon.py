"""Create a multi-resolution favicon from a raster image.

Examples:
    Create an ICO containing the default favicon sizes::

        uv run python scripts/create_favicon.py input.png favicon.ico

    Select specific sizes using a comma-separated list::

        uv run python scripts/create_favicon.py --sizes 16,32,48 input.png favicon.ico

For this project:
    Run the following:
        uv run python scripts/create_favicon.py \
            --sizes 16,32,48 \
            docs/assets/logo/dermapred-logo-small.png \
            docs/assets/logo/favicon.ico
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError

DEFAULT_SIZES = (16, 32, 48, 64, 128, 256)
MAX_ICO_SIZE = 256


def create_favicon(
    input_path: str | Path,
    output_path: str | Path,
    sizes: Sequence[int] = DEFAULT_SIZES,
) -> None:
    """Create a square, transparent ICO file containing the requested sizes.

    The input image is resized without changing its aspect ratio and centred on
    a transparent square canvas.

    Args:
        input_path: Raster image used as the favicon source.
        output_path: Destination ICO file.
        sizes: Square icon widths, in pixels. ICO supports sizes up to 256.

    Raises:
        FileNotFoundError: If the input file or output directory does not exist.
        ValueError: If no valid sizes are provided or both paths identify the
            same file.
        OSError: If Pillow cannot read the input or write the favicon.
    """
    source_path = Path(input_path).expanduser()
    destination_path = Path(output_path).expanduser()
    icon_sizes = _normalise_sizes(sizes)

    if not source_path.is_file():
        raise FileNotFoundError(f"Input image does not exist: {source_path}")
    if not destination_path.parent.is_dir():
        raise FileNotFoundError(f"Output directory does not exist: {destination_path.parent}")
    if source_path.resolve() == destination_path.resolve():
        raise ValueError("Input and output paths must be different")

    largest_size = max(icon_sizes)

    with Image.open(source_path) as image:
        # Honour camera orientation metadata before discarding image metadata.
        source_image = ImageOps.exif_transpose(image).convert("RGBA")
        source_image = ImageOps.contain(
            source_image,
            (largest_size, largest_size),
            method=Image.Resampling.LANCZOS,
        )

    favicon = Image.new(
        "RGBA",
        (largest_size, largest_size),
        color=(0, 0, 0, 0),
    )
    position = (
        (largest_size - source_image.width) // 2,
        (largest_size - source_image.height) // 2,
    )
    favicon.alpha_composite(source_image, dest=position)
    favicon.save(
        destination_path,
        format="ICO",
        sizes=[(size, size) for size in icon_sizes],
    )


def _normalise_sizes(sizes: Sequence[int]) -> tuple[int, ...]:
    """Validate, sort, and deduplicate ICO dimensions."""
    if not sizes:
        raise ValueError("At least one favicon size must be provided")

    invalid_sizes = [size for size in sizes if size < 1 or size > MAX_ICO_SIZE]
    if invalid_sizes:
        invalid_values = ", ".join(str(size) for size in invalid_sizes)
        raise ValueError(
            f"Favicon sizes must be between 1 and {MAX_ICO_SIZE} pixels; received: {invalid_values}"
        )

    return tuple(sorted(set(sizes)))


def _parse_sizes(value: str) -> tuple[int, ...]:
    """Parse a comma-separated list of dimensions for argparse."""
    try:
        sizes = tuple(int(item.strip()) for item in value.split(","))
        return _normalise_sizes(sizes)
    except ValueError as error:
        raise argparse.ArgumentTypeError(str(error)) from error


def _parse_args(arguments: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description=("Create a transparent, multi-resolution ICO favicon from a raster image.")
    )
    parser.add_argument("input", type=Path, help="source image")
    parser.add_argument("output", type=Path, help="destination .ico file")
    parser.add_argument(
        "--sizes",
        type=_parse_sizes,
        default=DEFAULT_SIZES,
        metavar="PX,...",
        help="comma-separated square icon sizes (default: 16,32,48,64,128,256)",
    )
    return parser.parse_args(arguments)


def main(arguments: Sequence[str] | None = None) -> int:
    """Run the favicon command-line interface."""
    args = _parse_args(arguments)

    try:
        create_favicon(args.input, args.output, args.sizes)
    except (FileNotFoundError, UnidentifiedImageError, OSError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1

    print(f"Created favicon: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
