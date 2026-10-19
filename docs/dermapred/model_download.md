# Releasing and downloading model weights

The Python package and trained artifacts have separate distribution paths:
PyPI distributes the code, while GitHub Releases distributes approved weights
and their matching probability calibrator. The private DVC remote remains the
record of the research artifacts. Package installation does not contact it or
download weights.

For issue approval, branches from `main`, model verification, and promotion
through a reviewed PR, see the [development and release
workflow](../development_workflow.md).

## Download a model

The desktop UI obtains the public manifest automatically when launched with
`python -m dermapred.ui`. It chooses the tag `vVERSION` using the installed
package version and requests the release asset named `model-release.json`.
`Predictor.from_release()` provides the same automatic selection for Python
users. The tag's release and assets must be published; a draft or an absent
development release produces an error. See the [desktop guide](ui.md) for
version overrides and offline use.

With the installed package and a trusted local manifest:

```bash
python -m dermapred.inference.download --manifest model-release.json
```

The command prints JSON containing the verified local paths for `weights` and
`calibrator`. It downloads on explicit request, reuses verified cached files,
and downloads a replacement if a cached file is corrupt. Cached files live
outside the installed package, under the platform's user cache directory.
Override the location with `--cache-dir PATH` or `DERMAPRED_CACHE_DIR`.

For a machine without network access, prefetch the files first, transfer the
manifest and cache, and then run:

```bash
python -m dermapred.inference.download \
  --manifest model-release.json --cache-dir /path/to/cache --offline
```

Offline mode makes no network requests. It fails explicitly if any file is
missing or does not match its expected size and checksum.

The Python API returns the same named paths:

```python
from pathlib import Path
from dermapred.inference.download import download_model

artifacts = download_model(Path("model-release.json"))
# Use artifacts["weights"] and artifacts["calibrator"] together.
```

The downloader retrieves files; it does not load the checkpoint or run
inference. Continue using `torch.load(..., map_location="cpu", weights_only=True)`
when loading a trusted checkpoint.

## Adapting the template

The manifest supports arbitrary named files, so a project can add tokenizer,
normalisation, or other inference assets alongside its weights. Newly generated
manifests use the package version by default. A software release can also select
an existing compatible model manifest, or use `--version` for a model with its
own release schedule.

Any public HTTPS host can serve the files. GitHub-specific APIs and credentials
are unnecessary for users. URLs and redirects must use HTTPS, downloads are
streamed into temporary files, and only files with the expected SHA-256 and
size are promoted into the cache. Hashes detect changed bytes; their authority
comes from the trusted manifest supplied with the software release.

Separate files are downloaded directly rather than extracting an archive.
The downloader uses Python's standard library and introduces no dependency on
DVC, GitHub clients, or a particular model hosting service.
