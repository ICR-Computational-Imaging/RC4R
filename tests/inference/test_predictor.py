"""Image inference must match training preprocessing and work without training extras."""

import io
import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest
import torch
from PIL import Image

from dermapred.data.preprocessing import preprocess_images
from dermapred.inference import Predictor
from dermapred.inference.calibration import ProbabilityCalibrator
from dermapred.inference.cli import main
from scripts.create_model_manifest import create_model_manifest


@pytest.fixture
def checkpoint(tmp_path: Path) -> Path:
    """Create an untrained deterministic checkpoint with rectangular input metadata."""
    from dermapred.models.binary_classifier import LeNetBinary

    model = LeNetBinary()
    for parameter in model.parameters():
        parameter.data.zero_()
    path = tmp_path / "model.pt"
    torch.save(
        {"model_state_dict": model.state_dict(), "input_channels": 3, "image_size": [28, 32]},
        path,
    )
    return path


def test_predictor_resizes_and_applies_training_preprocessing(checkpoint: Path) -> None:
    """Actual model input has the trained dimensions, RGB order, and [-1, 1] scale."""
    predictor = Predictor(checkpoint)
    seen: list[torch.Tensor] = []

    def capture_input(module: torch.nn.Module, inputs: tuple[torch.Tensor, ...]) -> None:
        seen.append(inputs[0].clone())

    handle = predictor.model.register_forward_pre_hook(capture_input)
    pixels = np.random.default_rng(42).integers(0, 256, (40, 50, 3), dtype=np.uint8)
    image = Image.fromarray(pixels)
    result = predictor.predict(image)
    handle.remove()
    resized = image.resize((32, 28), Image.Resampling.BILINEAR)
    np.testing.assert_array_equal(
        seen[0].numpy(), preprocess_images(np.asarray(resized)[None, ...])
    )
    assert not predictor.model.training
    assert not seen[0].requires_grad
    assert result.probability == result.raw_probability == 0.5
    assert result.label == "clinically_concerning"
    assert result.class_index == 1
    assert not result.calibrated


@pytest.mark.parametrize("mode", ["L", "RGBA"])
def test_predictor_accepts_non_rgb_images(checkpoint: Path, mode: str) -> None:
    assert Predictor(checkpoint).predict(Image.new(mode, (80, 40))).probability == 0.5


def test_predictor_applies_exif_orientation(checkpoint: Path) -> None:
    predictor = Predictor(checkpoint)
    seen: list[torch.Tensor] = []

    def capture_input(module: torch.nn.Module, inputs: tuple[torch.Tensor, ...]) -> None:
        seen.append(inputs[0].clone())

    handle = predictor.model.register_forward_pre_hook(capture_input)
    image = Image.fromarray(np.random.default_rng(0).integers(0, 256, (32, 28, 3), dtype=np.uint8))
    image.getexif()[274] = 6  # Rotate 90 degrees clockwise to display upright.
    predictor.predict(image)
    handle.remove()
    expected = image.transpose(Image.Transpose.ROTATE_270)
    np.testing.assert_array_equal(
        seen[0].numpy(), preprocess_images(np.asarray(expected)[None, ...])
    )


def test_predictor_uses_calibrator_and_threshold(checkpoint: Path, tmp_path: Path) -> None:
    calibrator = tmp_path / "calibrator.json"
    ProbabilityCalibrator("isotonic", np.array([0.0, 1.0]), np.array([0.2, 0.2])).save(calibrator)
    predictor = Predictor(checkpoint, calibrator_path=calibrator, threshold=0.3)
    result = predictor.predict(Image.new("RGB", (40, 40)))
    assert result.probability == 0.2
    assert result.raw_probability == 0.5
    assert result.label == "benign"
    assert result.class_index == 0
    assert result.calibrated


def test_legacy_checkpoint_requires_explicit_size(checkpoint: Path) -> None:
    data = torch.load(checkpoint, weights_only=True)
    del data["image_size"]
    torch.save(data, checkpoint)
    with pytest.raises(ValueError, match="lacks image_size"):
        Predictor(checkpoint)
    assert Predictor(checkpoint, image_size=28).image_size == (28, 28)


@pytest.mark.parametrize("size", [15, True, (28, 0), (28, 32, 28), 32])
def test_predictor_rejects_invalid_or_conflicting_size(checkpoint: Path, size: object) -> None:
    with pytest.raises(ValueError, match="image_size"):
        Predictor(checkpoint, image_size=size)  # type: ignore[arg-type]


@pytest.mark.parametrize("threshold", [float("nan"), float("inf"), -0.1, 1.1])
def test_predictor_rejects_invalid_threshold(checkpoint: Path, threshold: float) -> None:
    with pytest.raises(ValueError, match="threshold"):
        Predictor(checkpoint, threshold=threshold)


def test_predictor_rejects_non_rgb_checkpoint(checkpoint: Path) -> None:
    data = torch.load(checkpoint, weights_only=True)
    data["input_channels"] = 1
    torch.save(data, checkpoint)
    with pytest.raises(ValueError, match="RGB checkpoint"):
        Predictor(checkpoint)


def test_cli_accepts_image_file_and_prints_json(
    checkpoint: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    image = tmp_path / "image.png"
    Image.new("RGB", (60, 40)).save(image)
    assert main(["predict", str(image), "--model", str(checkpoint)]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["probability"] == 0.5
    assert result["class_index"] == 1
    assert not result["calibrated"]


def test_cli_reports_invalid_image(
    checkpoint: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["predict", str(tmp_path / "missing.png"), "--model", str(checkpoint)]) == 1
    assert "Inference failed" in capsys.readouterr().err


def test_manifest_api_uses_verified_cached_bundle(checkpoint: Path, tmp_path: Path) -> None:
    calibrator = tmp_path / "calibrator.json"
    ProbabilityCalibrator("platt", np.array([1.0]), np.array([-1.0])).save(calibrator)
    manifest = tmp_path / "manifest.json"
    create_model_manifest(
        "example",
        "1.0.0",
        "https://example.org/v1.0.0",
        {"weights": checkpoint, "calibrator": calibrator},
        manifest,
    )
    release = json.loads(manifest.read_text())
    cache = tmp_path / "cache"
    for artifact in release["files"].values():
        destination = cache / "example" / "1.0.0" / artifact["sha256"] / artifact["filename"]
        destination.parent.mkdir(parents=True)
        destination.write_bytes((tmp_path / artifact["filename"]).read_bytes())
    predictor = Predictor.from_manifest(manifest, cache_dir=cache, offline=True)
    result = predictor.predict(Image.new("RGB", (20, 20)))
    assert result.calibrated
    assert result.probability == pytest.approx(1 / (1 + np.exp(1)))
    # Verification must reject changed weights even when the file size is unchanged.
    weights = release["files"]["weights"]
    cached_weights = cache / "example" / "1.0.0" / weights["sha256"] / weights["filename"]
    cached_weights.write_bytes(b"0" * weights["size_bytes"])
    with pytest.raises(FileNotFoundError, match="verified cached"):
        Predictor.from_manifest(manifest, cache_dir=cache, offline=True)


def test_inference_does_not_import_training_dependencies(checkpoint: Path, tmp_path: Path) -> None:
    """A fresh interpreter can run both calibration methods with training imports blocked."""
    script = """
import importlib.abc
import sys
class BlockTraining(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path, target=None):
        if fullname.split(".")[0] in {"sklearn", "dvc", "monai", "medmnist", "matplotlib", "yaml"}:
            raise ImportError("Training dependency imported: " + fullname)
sys.meta_path.insert(0, BlockTraining())
import numpy as np
from PIL import Image
from pathlib import Path
from dermapred.inference import Predictor
from dermapred.inference.calibration import ProbabilityCalibrator
for method, x, y in [("platt", [1.0], [0.0]), ("isotonic", [0.0, 1.0], [0.0, 1.0])]:
    path = Path(sys.argv[2]) / (method + ".json")
    ProbabilityCalibrator(method, np.array(x), np.array(y)).save(path)
    result = Predictor(sys.argv[1], calibrator_path=path).predict(Image.new("RGB", (40, 40)))
    assert result.calibrated and result.probability == 0.5
"""
    source = Path(__file__).resolve().parents[2] / "src"
    result = subprocess.run(
        [sys.executable, "-c", script, str(checkpoint), str(tmp_path)],
        cwd=tmp_path,
        env={**os.environ, "PYTHONPATH": str(source), "OMP_NUM_THREADS": "2"},
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_public_release_api_fetches_matching_bundle_and_then_works_offline(
    checkpoint: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from dermapred.inference import download

    calibrator = tmp_path / "calibrator.json"
    ProbabilityCalibrator("platt", np.array([1.0]), np.array([-1.0])).save(calibrator)
    manifest = tmp_path / "model-release.json"
    base_url = "https://github.com/owner/project/releases/download/v1.0.0"
    create_model_manifest(
        "example", "1.0.0", base_url,
        {"weights": checkpoint, "calibrator": calibrator}, manifest,
    )
    payloads = {
        f"{base_url}/{path.name}": path.read_bytes()
        for path in (manifest, checkpoint, calibrator)
    }
    requested = []

    class Response(io.BytesIO):
        def geturl(self):
            return "https://release-assets.githubusercontent.com/file"

    class Opener:
        def open(self, request, timeout):
            requested.append(request.full_url)
            return Response(payloads[request.full_url])

    monkeypatch.setattr(download, "build_opener", lambda *args: Opener())
    monkeypatch.setattr(download, "package_version", lambda name: "1.0.0")
    options = {"repository": "owner/project", "cache_dir": tmp_path / "cache"}
    predictor = Predictor.from_release(**options)
    result = predictor.predict(Image.new("RGB", (20, 20)))
    assert result.calibrated
    assert result.probability == pytest.approx(1 / (1 + np.exp(1)))
    assert len(requested) == 3
    offline_predictor = Predictor.from_release(**options, offline=True)
    assert offline_predictor.predict(Image.new("RGB", (20, 20))) == result
    assert len(requested) == 3
