"""Tests for documentation figures that may not have been generated yet."""

from pathlib import Path
from types import SimpleNamespace

from scripts.docs_optional_figures import on_page_markdown

BLOCK = """<!-- optional-figure: ../../assets/evaluation/roc_curve.png | Test ROC curve -->
> **Results not yet available.** No ROC figure is available in this documentation yet.
<!-- /optional-figure -->"""


def _render(markdown: str, docs_dir: Path) -> str:
    page = SimpleNamespace(file=SimpleNamespace(src_uri="dermapred/dvc/evaluation.md"))
    return on_page_markdown(markdown, page=page, config={"docs_dir": str(docs_dir)})


def test_missing_figure_shows_placeholder(tmp_path: Path) -> None:
    """Docs should build without publishing a broken image link."""
    (tmp_path / "dermapred/dvc").mkdir(parents=True)
    rendered = _render(BLOCK, tmp_path)
    assert "Results not yet available" in rendered
    assert "![" not in rendered
    assert "optional-figure" not in rendered


def test_available_figure_replaces_placeholder(tmp_path: Path) -> None:
    """A published asset should appear automatically on the next docs build."""
    (tmp_path / "dermapred/dvc").mkdir(parents=True)
    figure = tmp_path / "assets/evaluation/roc_curve.png"
    figure.parent.mkdir(parents=True)
    figure.write_bytes(b"synthetic figure")
    assert _render(BLOCK, tmp_path) == "![Test ROC curve](../../assets/evaluation/roc_curve.png)"


def test_partial_results_keep_only_missing_placeholders(tmp_path: Path) -> None:
    """Each figure should be checked independently without altering ordinary links."""
    (tmp_path / "dermapred/dvc").mkdir(parents=True)
    figure = tmp_path / "assets/evaluation/roc_curve.png"
    figure.parent.mkdir(parents=True)
    figure.write_bytes(b"synthetic figure")
    other = BLOCK.replace("roc_curve.png", "confusion_matrix.png")
    ordinary = "![Required image](required.png)"
    rendered = _render(BLOCK + "\n\n" + other + "\n\n" + ordinary, tmp_path)
    assert rendered.count("Results not yet available") == 1
    assert "![Test ROC curve](../../assets/evaluation/roc_curve.png)" in rendered
    assert ordinary in rendered
