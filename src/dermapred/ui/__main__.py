"""Launch the PyQt6 image inference interface."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from functools import partial
from pathlib import Path

from dermapred.inference.download import DEFAULT_RELEASE_REPOSITORY
from dermapred.inference.predictor import Predictor
from dermapred.ui.app import run


def main(arguments: Sequence[str] | None = None) -> int:
    """Parse model configuration before loading the desktop libraries."""
    parser = argparse.ArgumentParser(
        description=__doc__,
        epilog="Without local model files or a manifest, use the public release matching "
        "the installed package version. Files are retrieved on the first inference.",
    )
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--manifest", type=Path, help="Trusted local model-release.json.")
    source.add_argument("--model", type=Path, help="Trusted local checkpoint.")
    parser.add_argument("--calibrator", type=Path, help="Matching local probability calibrator.")
    parser.add_argument("--image-size", type=int, help="Training size for legacy checkpoints.")
    parser.add_argument("--cache-dir", type=Path)
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--repo", default=DEFAULT_RELEASE_REPOSITORY, help="Public OWNER/REPO.")
    parser.add_argument("--release-version", help="Override the installed version (without v).")
    args = parser.parse_args(arguments)
    if args.model and not args.calibrator:
        parser.error("--model requires --calibrator for calibrated inference.")
    if args.calibrator and not args.model:
        parser.error("--calibrator is only used with --model; releases select their calibrator.")
    if args.model and (args.offline or args.cache_dir is not None):
        parser.error("--offline and --cache-dir apply to manifest or public-release downloads.")
    if (args.model or args.manifest) and (
        args.repo != DEFAULT_RELEASE_REPOSITORY or args.release_version is not None
    ):
        parser.error("--repo and --release-version apply only to automatic release selection.")

    if args.manifest:
        factory = partial(
            Predictor.from_manifest,
            args.manifest,
            cache_dir=args.cache_dir,
            offline=args.offline,
            image_size=args.image_size,
        )
    elif args.model:
        factory = partial(
            Predictor,
            args.model,
            calibrator_path=args.calibrator,
            image_size=args.image_size,
        )
    else:
        factory = partial(
            Predictor.from_release,
            repository=args.repo,
            version=args.release_version,
            cache_dir=args.cache_dir,
            offline=args.offline,
            image_size=args.image_size,
        )
    return run(factory)


if __name__ == "__main__":
    raise SystemExit(main())
