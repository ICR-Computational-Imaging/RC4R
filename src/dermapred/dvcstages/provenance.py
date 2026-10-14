"""Record SHA-256 identities for a trained model, calibrator, and supporting files.

This stage records local artifacts, not a release version or publication approval.
It uses only the standard library and never loads the model or accesses test data.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections.abc import Sequence
from pathlib import Path


def create_model_provenance(artifacts: dict[str, Path], output_path: Path) -> None:
    """Hash all inputs before writing a reproducible provenance record.

    The weights and calibrator roles are required. Additional roles can record
    parameters, validation evidence, or environment specifications. Existing
    output is replaced when DVC reruns the stage. No timestamp or Git revision
    is included: Git and DVC associate this output with the pipeline history.
    """
    if not {"weights", "calibrator"}.issubset(artifacts):
        raise ValueError("Both weights and calibrator artifacts are required.")
    files = {}
    for role, path in sorted(artifacts.items()):
        with path.open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
            size = stream.tell()
        files[role] = {"filename": path.name, "sha256": digest, "size_bytes": size}
    data = {"schema_version": 1, "hash_algorithm": "sha256", "files": files}
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main(arguments: Sequence[str] | None = None) -> int:
    """Create provenance from named files without retraining or publishing."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact", required=True, action="append", metavar="ROLE=PATH")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(arguments)
    artifacts: dict[str, Path] = {}
    for specification in args.artifact:
        role, separator, path = specification.partition("=")
        if not separator or not role or not path or role in artifacts:
            parser.error("Use distinct, non-empty --artifact ROLE=PATH arguments.")
        artifacts[role] = Path(path)
    try:
        create_model_provenance(artifacts, args.output)
    except (OSError, ValueError) as error:
        parser.exit(1, f"Provenance creation failed: {error}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
