"""Checks for reproducible identities of synthetic inference artifacts."""

import hashlib
import json
from pathlib import Path

import pytest

from dermapred.dvcstages.provenance import create_model_provenance, main


def test_provenance_hashes_exact_bytes_and_updates_calibrator(tmp_path: Path) -> None:
    weights = tmp_path / "weights.pt"
    calibrator = tmp_path / "calibrator.json"
    weights.write_bytes(b"synthetic weights")
    calibrator.write_bytes(b'{"coefficient": 1}')
    output = tmp_path / "outputs" / "model-provenance.json"
    artifacts = {"weights": weights, "calibrator": calibrator}
    create_model_provenance(artifacts, output)
    original = output.read_bytes()
    data = json.loads(original)
    assert data["files"]["weights"]["sha256"] == hashlib.sha256(weights.read_bytes()).hexdigest()
    assert data["files"]["weights"]["size_bytes"] == len(weights.read_bytes())
    create_model_provenance(dict(reversed(list(artifacts.items()))), output)
    assert output.read_bytes() == original
    calibrator.write_bytes(b'{"coefficient": 2}')
    create_model_provenance(artifacts, output)
    updated = json.loads(output.read_bytes())
    assert updated["files"]["weights"] == data["files"]["weights"]
    assert updated["files"]["calibrator"]["sha256"] != data["files"]["calibrator"]["sha256"]


def test_missing_input_does_not_replace_existing_provenance(tmp_path: Path) -> None:
    weights = tmp_path / "weights.pt"
    weights.write_bytes(b"synthetic")
    output = tmp_path / "provenance.json"
    output.write_text("previous provenance")
    with pytest.raises(FileNotFoundError):
        create_model_provenance(
            {"weights": weights, "calibrator": tmp_path / "missing.json"}, output
        )
    assert output.read_text() == "previous provenance"


def test_cli_rejects_duplicate_roles(tmp_path: Path) -> None:
    with pytest.raises(SystemExit) as error:
        main(["--artifact", "weights=a", "--artifact", "weights=b", "--output", str(tmp_path)])
    assert error.value.code == 2


def test_requires_both_inference_artifacts(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="weights and calibrator"):
        create_model_provenance({}, tmp_path / "provenance.json")
