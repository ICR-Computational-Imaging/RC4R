"""Test draft preparation against a simulated gh CLI, without contacting GitHub."""

import json
import subprocess
from pathlib import Path

import pytest

from scripts import upload_model_release as uploader
from scripts.create_model_manifest import create_model_manifest


class FakeGH:
    """Store draft assets and simulate gh's create, upload, and download commands."""

    def __init__(self) -> None:
        self.calls: list[list[str]] = []
        self.draft: bool | None = None
        self.assets: dict[str, bytes] = {}
        self.tag_exists = True
        self.api_error = ""
        self.interrupt_upload = False
        self.corrupt_download = False
        self.notes: str | None = None
        self.include_older_release = False

    def run(
        self, command: list[str], *, capture_output: bool, text: bool, stdin: int
    ) -> subprocess.CompletedProcess[str]:
        self.calls.append(command)
        assert capture_output and text and stdin == subprocess.DEVNULL
        assert command[0] == "gh"
        assert "--clobber" not in command
        if command[1] == "api":
            assert command[2:4] == ["--hostname", "github.com"]
            if "/git/ref/tags/" in command[-1]:
                if not self.tag_exists:
                    return subprocess.CompletedProcess(command, 1, "", "Not Found (HTTP 404)")
                return subprocess.CompletedProcess(command, 0, '{"ref":"refs/tags/v0.1.0"}', "")
            if self.api_error:
                return subprocess.CompletedProcess(command, 1, "", self.api_error)
            if self.draft is None:
                return subprocess.CompletedProcess(command, 0, "[[]]", "")
            data = {
                "draft": self.draft,
                "tag_name": "v0.1.0",
                "assets": [{"name": name} for name in self.assets],
                "html_url": "https://github.com/owner/project/releases/tag/v0.1.0",
            }
            assert "--paginate" in command and "--slurp" in command
            pages = [[data]]
            if self.include_older_release:
                pages.insert(0, [{"tag_name": "v0.0.1", "draft": False, "assets": []}])
            return subprocess.CompletedProcess(command, 0, json.dumps(pages), "")
        assert command[1] == "release"
        assert command[3] == "v0.1.0"
        assert command[command.index("--repo") + 1] == "github.com/owner/project"
        action = command[2]
        if action == "create":
            assert self.draft is None
            assert "--draft" in command and "--verify-tag" in command
            # gh rejects --notes-from-tag combined with the explicit --repo.
            assert "--notes-from-tag" not in command
            if "--notes-file" in command:
                assert "--generate-notes" not in command
                self.notes = Path(command[command.index("--notes-file") + 1]).read_text()
            else:
                assert "--generate-notes" in command
                self.notes = "Automatically generated release notes"
            self.draft = True
        elif action == "upload":
            assert self.draft is True
            for name in command[4 : command.index("--repo")]:
                path = Path(name)
                assert path.name not in self.assets
                self.assets[path.name] = path.read_bytes()
                if self.interrupt_upload:
                    self.interrupt_upload = False
                    return subprocess.CompletedProcess(command, 1, "", "Upload interrupted")
        elif action == "download":
            filename = command[command.index("--pattern") + 1]
            directory = Path(command[command.index("--dir") + 1])
            payload = b"corrupt" if self.corrupt_download else self.assets[filename]
            (directory / filename).write_bytes(payload)
        else:
            raise AssertionError(f"Unexpected gh operation: {command}")
        return subprocess.CompletedProcess(command, 0, "", "")


@pytest.fixture
def bundle(tmp_path: Path) -> tuple[Path, dict[str, Path]]:
    weights = tmp_path / "model.pt"
    calibrator = tmp_path / "calibrator.json"
    weights.write_bytes(b"approved weights")
    calibrator.write_bytes(b"approved calibration")
    artifacts = {"weights": weights, "calibrator": calibrator}
    manifest = tmp_path / "model-release.json"
    create_model_manifest(
        "example",
        "0.1.0",
        "https://github.com/owner/project/releases/download/v0.1.0",
        artifacts,
        manifest,
    )
    return manifest, artifacts


@pytest.fixture
def fake_gh(monkeypatch: pytest.MonkeyPatch) -> FakeGH:
    client = FakeGH()
    monkeypatch.setattr(subprocess, "run", client.run)
    return client


def test_creates_draft_and_verifies_uploaded_bytes(
    bundle: tuple[Path, dict[str, Path]], fake_gh: FakeGH
) -> None:
    manifest, artifacts = bundle
    result = uploader.upload_model_release("owner/project", manifest, artifacts)
    assert result == "https://github.com/owner/project/releases/tag/v0.1.0"
    assert fake_gh.draft is True
    assert fake_gh.assets == {
        manifest.name: manifest.read_bytes(),
        **{path.name: path.read_bytes() for path in artifacts.values()},
    }
    assert sum(call[1:3] == ["release", "download"] for call in fake_gh.calls) == 3
    create = next(call for call in fake_gh.calls if call[1:3] == ["release", "create"])
    assert "--generate-notes" in create
    assert "--repo" in create
    assert fake_gh.notes == "Automatically generated release notes"


def test_dry_run_only_checks_local_files(
    bundle: tuple[Path, dict[str, Path]], fake_gh: FakeGH
) -> None:
    manifest, artifacts = bundle
    result = uploader.upload_model_release("owner/project", manifest, artifacts, dry_run=True)
    assert "Verified 3 local files" in result
    assert "remote tag and draft have not been checked" in result
    assert fake_gh.calls == []


def test_changed_model_fails_before_contacting_github(
    bundle: tuple[Path, dict[str, Path]], fake_gh: FakeGH
) -> None:
    manifest, artifacts = bundle
    artifacts["weights"].write_bytes(b"tampered weights")
    with pytest.raises(ValueError, match="size and SHA-256"):
        uploader.upload_model_release("owner/project", manifest, artifacts)
    assert fake_gh.calls == []


@pytest.mark.parametrize("repository", ["other/project", "owner/other", "invalid"])
def test_wrong_repository_fails_before_upload(
    bundle: tuple[Path, dict[str, Path]], fake_gh: FakeGH, repository: str
) -> None:
    manifest, artifacts = bundle
    with pytest.raises(ValueError):
        uploader.upload_model_release(repository, manifest, artifacts)
    assert fake_gh.calls == []


def test_missing_role_fails_before_upload(
    bundle: tuple[Path, dict[str, Path]], fake_gh: FakeGH
) -> None:
    manifest, artifacts = bundle
    with pytest.raises(ValueError, match="every manifest role"):
        uploader.upload_model_release("owner/project", manifest, {"weights": artifacts["weights"]})
    assert fake_gh.calls == []


def test_missing_tag_never_creates_one_or_uploads(
    bundle: tuple[Path, dict[str, Path]], fake_gh: FakeGH
) -> None:
    fake_gh.tag_exists = False
    with pytest.raises(RuntimeError, match="404"):
        uploader.upload_model_release("owner/project", *bundle)
    assert len(fake_gh.calls) == 1
    assert fake_gh.draft is None


def test_published_release_is_never_modified(
    bundle: tuple[Path, dict[str, Path]], fake_gh: FakeGH
) -> None:
    fake_gh.draft = False
    with pytest.raises(ValueError, match="already published"):
        uploader.upload_model_release("owner/project", *bundle)
    assert all(call[1] == "api" for call in fake_gh.calls)


def test_authentication_failure_is_not_treated_as_missing_release(
    bundle: tuple[Path, dict[str, Path]], fake_gh: FakeGH
) -> None:
    fake_gh.api_error = "Authentication failed (HTTP 401)"
    with pytest.raises(RuntimeError, match="Authentication failed"):
        uploader.upload_model_release("owner/project", *bundle)
    assert fake_gh.draft is None
    assert all(call[1] == "api" for call in fake_gh.calls)


def test_matching_existing_assets_are_reused_on_retry(
    bundle: tuple[Path, dict[str, Path]], fake_gh: FakeGH
) -> None:
    manifest, artifacts = bundle
    fake_gh.draft = True
    fake_gh.assets["model.pt"] = artifacts["weights"].read_bytes()
    uploader.upload_model_release("owner/project", manifest, artifacts)
    upload = next(call for call in fake_gh.calls if call[1:3] == ["release", "upload"])
    assert {Path(path).name for path in upload[4 : upload.index("--repo")]} == {
        "model-release.json",
        "calibrator.json",
    }
    fake_gh.calls.clear()
    uploader.upload_model_release("owner/project", manifest, artifacts)
    assert not any(call[1:3] == ["release", "upload"] for call in fake_gh.calls)


def test_conflicting_existing_asset_is_not_overwritten(
    bundle: tuple[Path, dict[str, Path]], fake_gh: FakeGH
) -> None:
    fake_gh.draft = True
    fake_gh.assets["model.pt"] = b"different model"
    with pytest.raises(ValueError, match="nothing will be overwritten"):
        uploader.upload_model_release("owner/project", *bundle)
    assert fake_gh.assets == {"model.pt": b"different model"}
    assert not any(call[1:3] == ["release", "upload"] for call in fake_gh.calls)


def test_partial_upload_can_be_completed_by_retry(
    bundle: tuple[Path, dict[str, Path]], fake_gh: FakeGH
) -> None:
    fake_gh.interrupt_upload = True
    with pytest.raises(RuntimeError, match="Upload interrupted"):
        uploader.upload_model_release("owner/project", *bundle)
    assert fake_gh.draft is True
    assert len(fake_gh.assets) == 1
    uploader.upload_model_release("owner/project", *bundle)
    assert len(fake_gh.assets) == 3


def test_existing_draft_is_found_on_later_release_page(
    bundle: tuple[Path, dict[str, Path]], fake_gh: FakeGH
) -> None:
    fake_gh.draft = True
    fake_gh.include_older_release = True
    uploader.upload_model_release("owner/project", *bundle)
    assert len(fake_gh.assets) == 3
    assert not any(call[1:3] == ["release", "create"] for call in fake_gh.calls)


def test_download_verification_detects_corrupt_remote_bytes(
    bundle: tuple[Path, dict[str, Path]], fake_gh: FakeGH
) -> None:
    fake_gh.corrupt_download = True
    with pytest.raises(ValueError, match="differs from the approved"):
        uploader.upload_model_release("owner/project", *bundle)
    assert fake_gh.draft is True


def test_release_notes_file_is_passed_to_gh(
    tmp_path: Path, bundle: tuple[Path, dict[str, Path]], fake_gh: FakeGH
) -> None:
    notes = tmp_path / "notes.md"
    notes.write_text("Release 0.1.0\n\nApproved model and calibration.\n")
    uploader.upload_model_release("owner/project", *bundle, notes_path=notes)
    assert fake_gh.notes == notes.read_text()


def test_existing_draft_preserves_reviewed_notes(
    tmp_path: Path, bundle: tuple[Path, dict[str, Path]], fake_gh: FakeGH
) -> None:
    fake_gh.draft = True
    fake_gh.notes = "Notes already reviewed on GitHub."
    notes = tmp_path / "replacement.md"
    notes.write_text("These must not replace existing draft notes.")
    uploader.upload_model_release("owner/project", *bundle, notes_path=notes)
    assert fake_gh.notes == "Notes already reviewed on GitHub."
    assert not any(call[1:3] == ["release", "create"] for call in fake_gh.calls)


def test_missing_gh_reports_installation_instructions(
    bundle: tuple[Path, dict[str, Path]], monkeypatch: pytest.MonkeyPatch
) -> None:
    def missing(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        raise FileNotFoundError("gh")

    monkeypatch.setattr(subprocess, "run", missing)
    with pytest.raises(RuntimeError, match="Install GitHub CLI"):
        uploader.upload_model_release("owner/project", *bundle)


def test_cli_dry_run_reports_success(
    bundle: tuple[Path, dict[str, Path]], fake_gh: FakeGH, capsys: pytest.CaptureFixture[str]
) -> None:
    manifest, artifacts = bundle
    arguments = ["--repo", "owner/project", "--manifest", str(manifest), "--dry-run"]
    for role, path in artifacts.items():
        arguments.extend(["--artifact", f"{role}={path}"])
    assert uploader.main(arguments) == 0
    assert "Verified 3 local files" in capsys.readouterr().out
    assert fake_gh.calls == []
