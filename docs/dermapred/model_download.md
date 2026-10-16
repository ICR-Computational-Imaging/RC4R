# Releasing and downloading model weights

The Python package and trained artifacts have separate distribution paths:
PyPI distributes the code, while GitHub Releases distributes approved weights
and their matching probability calibrator. The private DVC remote remains the
record of the research artifacts. Package installation does not contact it or
download weights.

For issue approval, branches from `main`, model verification, and promotion
through a reviewed PR, see the [development and release
workflow](../development_workflow.md).

## Prepare a release

The training pipeline creates a [model provenance record](dvc/provenance.md)
after training and calibration. This records file hashes without a release
version or public URLs. Prepare the release manifest below separately once
the final release version and selected artifacts are known.

First identify the code commit and corresponding DVC checkpoint and calibrator.
Retrieve those artifacts inside the institutional environment. Public release
of those specific artifacts must be permitted; changing the download mechanism
does not change their publication status.

After bumpversion has set the approved release version, generate a manifest locally:

```bash
uv run python -m scripts.create_model_manifest \
  --name dermapred-lenet \
  --base-url 'https://github.com/ICR-Computational-Imaging/RC4R/releases/download/v{version}' \
  --artifact weights=results/trained_models/binary_classifier.pt \
  --artifact calibrator=results/calibration/probability_calibrator.json \
  --output model-release.json
```

The generator reads the repository's `VERSION` file automatically. If it contains
`0.1.0`, the manifest version is `0.1.0` and the download URLs contain `v0.1.0`.
Preview versions such as `0.1.0.dev4` work the same way. You do not need to type
the version twice or add generated manifests to `.bumpversion.cfg`.

Generate the manifest after the release version is set and before reviewing
the release PR. Changing `VERSION` does not rewrite a previously generated
manifest: create a fresh manifest after a bump and review it before replacing
the older one. The generator refuses to overwrite existing files. For a model
whose version is independent of the package, use an explicit `--version`;
`--version-file PATH` selects a different version file instead.

This creates metadata only. It does not upload files, retrieve DVC artifacts,
or alter the checkpoint. Each file entry records a URL, filename, SHA-256, and
byte count calculated from the local file. The generator refuses to overwrite
an existing manifest. Keep a record of the source commit and DVC hashes with
the release, along with the model licence, preprocessing specification, class
definitions, evaluation results, and research-use limitations.

Use the draft upload command below to attach the exact checkpoint, calibrator,
and `model-release.json` to the matching GitHub release. Use version-specific
download URLs, not `latest`.
If supported by repository policy, enable immutable releases so that published
tags and assets cannot be replaced. See [GitHub's release
documentation](https://docs.github.com/en/repositories/releasing-projects-on-github/managing-releases-in-a-repository).

The manifest should also be distributed with the corresponding software
version so users have a trusted record of the expected hashes. Once a real
release is chosen, it can be included as package data. The template does not
ship a default manifest or claim that a public model release already exists.

## Upload the files to a draft GitHub Release

**Responsible: maintainer, after the release PR is merged and its tag is pushed.**

Install [GitHub CLI](https://cli.github.com/) (`gh`) and sign in once:

```bash
gh auth login
```

The uploader reads the tag from the manifest: version `0.1.0` selects `v0.1.0`.
It requires that tag to already exist on GitHub. It does not create or push tags,
download private DVC files, or publish a release.

First check the files locally, without contacting GitHub:

```bash
uv run --locked python -m scripts.upload_model_release \
  --repo ICR-Computational-Imaging/RC4R \
  --manifest model-release.json \
  --artifact weights=results/trained_models/binary_classifier.pt \
  --artifact calibrator=results/calibration/probability_calibrator.json \
  --dry-run
```

**Expected result:** a message saying that three local files were verified.
This checks the manifest URLs and each artifact's size and SHA-256. It does not
check GitHub authentication, the remote tag, or the draft release.

To upload, run the same command without `--dry-run`:

```bash
uv run --locked python -m scripts.upload_model_release \
  --repo ICR-Computational-Imaging/RC4R \
  --manifest model-release.json \
  --artifact weights=results/trained_models/binary_classifier.pt \
  --artifact calibrator=results/calibration/probability_calibrator.json
```

**This is the step that sends the model files to GitHub.** The script calls
`gh release create --draft --verify-tag` when a draft is needed, then
`gh release upload`. It downloads the attachments through authenticated `gh`
and verifies their hashes before reporting success. See [creating
releases](https://cli.github.com/manual/gh_release_create) and [uploading
assets](https://cli.github.com/manual/gh_release_upload) in the GitHub CLI manual.

**Expected result:** the script prints a draft release link. Open GitHub's
**Releases** page while signed in, review the draft's notes and attachments, and
click **Publish release** when approved. The public downloader URLs become
available after publication. Model verification and permission to distribute
the files must already be established; hash checks confirm file identity.

For a new draft, the script passes `--generate-notes` so GitHub creates release
notes automatically. No temporary notes file is required. Review and edit the
generated notes in the draft before publishing, adding model changes and
limitations where needed. Add `--notes-file PATH` to use your own reviewed
notes instead. Existing draft notes are preserved when an upload is retried;
the script does not regenerate or replace them. Development versions are
marked as prereleases.

An interrupted upload can leave a partial draft. Rerun the command: it checks
existing attachments, reuses identical files, and uploads only missing ones.
It refuses to overwrite different files or modify a published release. Local
files are snapshotted before upload so the bytes checked are the bytes sent.
Remote verification downloads the uploaded files again, which uses additional
bandwidth for large models.

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
