"""Tests for documentation figures that may not have been generated yet."""

from pathlib import Path
from types import SimpleNamespace

import pytest

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


METRICS_BLOCK = """<!-- optional-metrics: ../../assets/evaluation/test_metrics.csv -->
> **Results not yet available.** No evaluation metrics report is available here.
<!-- /optional-metrics -->"""


def test_missing_metrics_shows_placeholder(tmp_path: Path) -> None:
    """A missing evaluation report should not break the documentation build."""
    (tmp_path / "dermapred/dvc").mkdir(parents=True)
    rendered = _render(METRICS_BLOCK, tmp_path)
    assert "Results not yet available" in rendered
    assert "optional-metrics" not in rendered


def test_metrics_csv_renders_estimates_intervals_and_context(tmp_path: Path) -> None:
    """Available results should show numeric intervals and the chosen threshold."""
    (tmp_path / "dermapred/dvc").mkdir(parents=True)
    report = tmp_path / "assets/evaluation/test_metrics.csv"
    report.parent.mkdir(parents=True)
    report.write_text(
        "metric,value,ci_lower,ci_upper\n"
        "roc_auc,0.812345,0.7,0.9\n"
        "sensitivity,0.75,0.6,0.85\n"
        "threshold,0.5,,\n"
        "sample_count,20,,\n", encoding="utf-8"
    )
    rendered = _render(METRICS_BLOCK, tmp_path)
    assert "| ROC AUC | 0.8123 | 0.7000 | 0.9000 |" in rendered
    assert "| Sensitivity | 0.7500 | 0.6000 | 0.8500 |" in rendered
    assert "| Threshold | 0.5 |" in rendered
    assert "| Sample count | 20 |" in rendered
    assert "Results not yet available" not in rendered
    report.unlink()
    assert "Results not yet available" in _render(METRICS_BLOCK, tmp_path)


def test_invalid_metrics_are_not_silently_hidden(tmp_path: Path) -> None:
    """Malformed published reports should fail clearly instead of hiding errors."""
    (tmp_path / "dermapred/dvc").mkdir(parents=True)
    report = tmp_path / "assets/evaluation/test_metrics.csv"
    report.parent.mkdir(parents=True)
    report.write_text("wrong,columns\n1,2\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Invalid evaluation metrics CSV schema"):
        _render(METRICS_BLOCK, tmp_path)
