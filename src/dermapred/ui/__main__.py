"""Launch the optional PyQt6 image inference interface."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from functools import partial
from pathlib import Path


def main(arguments: Sequence[str] | None = None) -> int:
    """Parse model configuration before loading the optional desktop libraries."""
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--manifest", type=Path, help="Trusted local model-release.json.")
    source.add_argument("--model", type=Path, help="Trusted local checkpoint.")
    parser.add_argument("--calibrator", type=Path, help="Matching local probability calibrator.")
    parser.add_argument("--image-size", type=int, help="Training size for legacy checkpoints.")
    parser.add_argument("--cache-dir", type=Path)
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args(arguments)
    if args.model and not args.calibrator:
        parser.error("--model requires --calibrator for calibrated inference.")
    if args.manifest and args.calibrator:
        parser.error("The manifest selects its calibrator; do not supply --calibrator.")
    if args.model and (args.offline or args.cache_dir is not None):
        parser.error("--offline and --cache-dir require --manifest.")
    try:
        from dermapred.inference.predictor import Predictor
        from dermapred.ui.app import run
    except ImportError as error:
        print(f"UI dependencies unavailable: {error}. Install 'dermapred[ui]'.", file=sys.stderr)
        return 1
    if args.manifest:
        factory = partial(
            Predictor.from_manifest,
            args.manifest,
            cache_dir=args.cache_dir,
            offline=args.offline,
            image_size=args.image_size,
        )
    else:
        factory = partial(
            Predictor,
            args.model,
            calibrator_path=args.calibrator,
            image_size=args.image_size,
        )
    return run(factory)


if __name__ == "__main__":
    raise SystemExit(main())
