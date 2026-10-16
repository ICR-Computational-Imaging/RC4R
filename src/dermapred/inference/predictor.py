"""Image-file inference using the same pixel scaling as the training pipeline."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import torch
from PIL import Image, ImageOps

from dermapred.data.preprocessing import preprocess_images
from dermapred.inference.calibration import ProbabilityCalibrator, logits_to_probabilities
from dermapred.inference.download import (
    DEFAULT_RELEASE_REPOSITORY,
    ModelRelease,
    download_model,
    download_release_manifest,
)
from dermapred.models.binary_classifier import LeNetBinary


def _image_size(value: object) -> tuple[int, int]:
    """Validate the trained image dimensions, stored in height/width order."""
    if type(value) is int:
        value = (value, value)
    if (
        not isinstance(value, (list, tuple))
        or len(value) != 2
        or any(type(dimension) is not int or dimension < 16 for dimension in value)
    ):
        raise ValueError("image_size must be an integer or (height, width), each at least 16.")
    return int(value[0]), int(value[1])


@dataclass(frozen=True)
class Prediction:
    """A binary prediction and its probability for the positive class."""

    label: str
    class_index: int
    probability: float
    raw_probability: float
    threshold: float
    calibrated: bool

    def to_dict(self) -> dict[str, str | int | float | bool]:
        """Return JSON-compatible values for a CLI or future user interface."""
        return asdict(self)


class Predictor:
    """Load a model once and classify image paths or Pillow images on the CPU.

    Images are oriented according to EXIF metadata, converted to RGB, resized
    directly to the training dimensions with bilinear interpolation, then
    scaled to [-1, 1] and converted to channels-first tensors. Resizing a
    non-square image changes its aspect ratio; no crop or padding is applied.
    """

    def __init__(
        self,
        model_path: str | Path,
        *,
        calibrator_path: str | Path | None = None,
        image_size: int | tuple[int, int] | None = None,
        threshold: float = 0.5,
    ) -> None:
        """Load local artifacts without downloading or accessing training data.

        Args:
            model_path: Trusted training checkpoint containing model_state_dict.
            calibrator_path: Optional JSON mapping fitted using validation data.
            image_size: Explicit dimensions for legacy checkpoints. When the
                checkpoint has image_size metadata, an override must match it.
            threshold: Fixed positive-class threshold agreed before evaluation.

        Raises:
            OSError: If local artifacts cannot be read.
            ValueError: If input dimensions, checkpoint metadata, or settings
                are missing or incompatible with RGB image inference.
        """
        if not np.isfinite(threshold) or not 0 <= threshold <= 1:
            raise ValueError("threshold must be finite and between zero and one.")
        checkpoint = torch.load(Path(model_path), map_location="cpu", weights_only=True)
        if not isinstance(checkpoint, dict) or "model_state_dict" not in checkpoint:
            raise ValueError("Checkpoint must contain model_state_dict.")
        if type(checkpoint.get("input_channels")) is not int or checkpoint["input_channels"] != 3:
            raise ValueError("Image-file inference requires a three-channel RGB checkpoint.")
        stored_size = checkpoint.get("image_size")
        if stored_size is None and image_size is None:
            raise ValueError(
                "Checkpoint lacks image_size metadata; supply its training image_size explicitly."
            )
        dimensions = _image_size(stored_size if stored_size is not None else image_size)
        if image_size is not None and _image_size(image_size) != dimensions:
            raise ValueError("image_size override does not match the checkpoint's training size.")
        self.image_size = dimensions
        self.threshold = float(threshold)
        self.model = LeNetBinary(input_channels=3)
        self.model.load_state_dict(checkpoint["model_state_dict"])
        self.model.eval()
        self.calibrator = (
            None if calibrator_path is None else ProbabilityCalibrator.load(Path(calibrator_path))
        )

    @classmethod
    def from_manifest(
        cls,
        manifest_path: str | Path,
        *,
        cache_dir: Path | None = None,
        offline: bool = False,
        image_size: int | tuple[int, int] | None = None,
        threshold: float = 0.5,
    ) -> Predictor:
        """Download and verify a pinned release, then load its weights and calibrator.

        A trusted manifest must declare both weights and calibrator artifacts.
        Offline mode uses verified cached files and makes no network requests.
        Legacy weights require image_size as for the local constructor.
        """
        manifest = Path(manifest_path)
        release = ModelRelease.load(manifest)
        if not {"weights", "calibrator"} <= release.files.keys():
            raise ValueError("Inference manifest must contain weights and calibrator artifacts.")
        paths = download_model(manifest, cache_dir=cache_dir, offline=offline)
        return cls(
            paths["weights"],
            calibrator_path=paths["calibrator"],
            image_size=image_size,
            threshold=threshold,
        )

    @classmethod
    def from_release(
        cls,
        *,
        repository: str = DEFAULT_RELEASE_REPOSITORY,
        version: str | None = None,
        cache_dir: Path | None = None,
        offline: bool = False,
        image_size: int | tuple[int, int] | None = None,
        threshold: float = 0.5,
    ) -> Predictor:
        """Load a public model release matching the installed package version.

        The matching tag must publish ``model-release.json`` alongside the
        weights and calibrator. No fallback to ``latest`` or another version
        occurs. ``version`` can explicitly select a different published release.
        """
        manifest = download_release_manifest(
            repository=repository, version=version, cache_dir=cache_dir, offline=offline
        )
        return cls.from_manifest(
            manifest,
            cache_dir=cache_dir,
            offline=offline,
            image_size=image_size,
            threshold=threshold,
        )

    def predict(self, image: str | Path | Image.Image) -> Prediction:
        """Classify one input image and return calibrated or raw probabilities.

        Args:
            image: Image filename or an already opened Pillow image.

        Returns:
            Probability for clinically_concerning, class index, and class label.
            If no calibrator was supplied, probability equals raw_probability.

        Raises:
            OSError: If a file cannot be decoded as an image.
            TypeError: If image is neither a path nor a Pillow image.
            ValueError: If inference produces a non-finite or invalid probability.
        """
        if isinstance(image, (str, Path)):
            with Image.open(image) as opened:
                return self.predict(opened)
        if not isinstance(image, Image.Image):
            raise TypeError("image must be a filename, pathlib.Path, or Pillow image.")
        height, width = self.image_size
        rgb = ImageOps.exif_transpose(image).convert("RGB")
        if rgb.size != (width, height):
            rgb = rgb.resize((width, height), resample=Image.Resampling.BILINEAR)
        batch = preprocess_images(np.asarray(rgb)[None, ...])
        with torch.inference_mode():
            logits = self.model(torch.from_numpy(batch)).numpy().reshape(-1)
        raw = float(logits_to_probabilities(logits)[0])
        probability = (
            raw if self.calibrator is None else float(self.calibrator.predict_proba(logits)[0])
        )
        if not np.isfinite(probability) or not 0 <= probability <= 1:
            raise ValueError("Model calibration must return a finite probability in [0, 1].")
        class_index = int(probability >= self.threshold)
        return Prediction(
            label=("benign", "clinically_concerning")[class_index],
            class_index=class_index,
            probability=probability,
            raw_probability=raw,
            threshold=self.threshold,
            calibrated=self.calibrator is not None,
        )
