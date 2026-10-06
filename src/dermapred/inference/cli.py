"""Command-line image inference for the installed dermapred package."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from dermapred.inference.predictor import Predictor


def main(arguments: Sequence[str] | None = None) -> int:
    """Run one image through local weights or a verified manifest release."""
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    predict = commands.add_parser("predict", help="Classify an image and print JSON.")
    predict.add_argument("image", type=Path)
    source = predict.add_mutually_exclusive_group(required=True)
    source.add_argument("--manifest", type=Path)
    source.add_argument("--model", type=Path)
    predict.add_argument("--calibrator", type=Path)
    predict.add_argument(
        "--image-size", type=int, help="Training size for legacy square checkpoints."
    )
    predict.add_argument("--threshold", type=float, default=0.5)
    predict.add_argument("--cache-dir", type=Path)
    predict.add_argument("--offline", action="store_true")
    args = parser.parse_args(arguments)
    if args.manifest and args.calibrator:
        parser.error("--calibrator is only used with --model; manifests select the calibrator.")
    if args.model and (args.cache_dir is not None or args.offline):
        parser.error("--cache-dir and --offline are only used with --manifest.")
    try:
        if args.manifest:
            predictor = Predictor.from_manifest(
                args.manifest,
                cache_dir=args.cache_dir,
                offline=args.offline,
                image_size=args.image_size,
                threshold=args.threshold,
            )
        else:
            predictor = Predictor(
                args.model,
                calibrator_path=args.calibrator,
                image_size=args.image_size,
                threshold=args.threshold,
            )
        result = predictor.predict(args.image)
    except (OSError, ValueError, KeyError, TypeError, RuntimeError) as error:
        print(f"Inference failed: {error}", file=sys.stderr)
        return 1
    print(json.dumps(result.to_dict(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
