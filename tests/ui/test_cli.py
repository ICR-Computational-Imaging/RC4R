"""UI launch validation, without displaying a window or loading model files."""

from unittest.mock import Mock

import pytest

from dermapred.ui.__main__ import main


@pytest.mark.parametrize(
    "arguments",
    [[], ["--model", "weights.pt"],
     ["--manifest", "release.json", "--calibrator", "calibrator.json"],
     ["--model", "weights.pt", "--calibrator", "calibrator.json", "--offline"]],
)
def test_invalid_cli_arguments(arguments):
    with pytest.raises(SystemExit) as error:
        main(arguments)
    assert error.value.code == 2


@pytest.mark.parametrize("manifest", [True, False])
def test_launch_configures_existing_predictor_api(monkeypatch, manifest):
    pytest.importorskip("PyQt6")
    from dermapred.inference import predictor
    from dermapred.ui import app

    factory = Mock()
    monkeypatch.setattr(predictor, "Predictor", factory)
    monkeypatch.setattr(app, "run", lambda configure: (configure(), 0)[1])
    if manifest:
        assert main(["--manifest", "release.json", "--offline", "--cache-dir", "cache"]) == 0
        assert factory.from_manifest.call_args.kwargs["offline"] is True
    else:
        assert main(["--model", "weights.pt", "--calibrator", "calibrator.json",
                     "--image-size", "64"]) == 0
        assert factory.call_args.kwargs["image_size"] == 64
