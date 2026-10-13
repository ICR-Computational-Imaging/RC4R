"""Show available figures and metrics or their existing placeholders during MkDocs builds.

Registered through ``hooks`` in mkdocs.yaml. An optional figure block starts
with ``<!-- optional-figure: relative/path.png | Figure description -->`` and
ends with ``<!-- /optional-figure -->``. Paths are relative to the source page.
Metrics blocks use ``<!-- optional-metrics: relative/path.csv -->`` and
``<!-- /optional-metrics -->``. The block body is fallback Markdown for missing
files. Metrics CSV files use the evaluation stage schema: metric, value,
ci_lower, ci_upper.
This hook reads documentation assets only and never runs a research pipeline.
"""

from __future__ import annotations

import csv
import re
from pathlib import Path
from typing import Any

OPTIONAL_FIGURE = re.compile(
    r"^<!-- optional-figure: (?P<path>[^|\n]+) \| (?P<alt>[^\n]+) -->\n"
    r"(?P<fallback>.*?)^<!-- /optional-figure -->$",
    re.MULTILINE | re.DOTALL,
)


OPTIONAL_METRICS = re.compile(
    r"^<!-- optional-metrics: (?P<path>[^\n]+) -->\n"
    r"(?P<fallback>.*?)^<!-- /optional-metrics -->$",
    re.MULTILINE | re.DOTALL,
)


def _metrics_table(path: Path) -> str:
    """Render evaluation estimates, bootstrap intervals, and context from CSV.

    Args:
        path: CSV written by the evaluation stage.

    Returns:
        Markdown tables containing metrics and evaluation context.

    Raises:
        ValueError: If the report is empty or its CSV schema is invalid.
        OSError: If the report cannot be read.
    """
    with path.open(encoding="utf-8", newline="") as source:
        reader = csv.DictReader(source)
        if reader.fieldnames != ["metric", "value", "ci_lower", "ci_upper"]:
            raise ValueError(f"Invalid evaluation metrics CSV schema: {path}")
        rows = list(reader)
    if not rows:
        raise ValueError(f"Evaluation metrics CSV contains no results: {path}")
    metrics = ["| Metric | Value | CI lower | CI upper |", "| --- | ---: | ---: | ---: |"]
    context = ["| Evaluation context | Value |", "| --- | --- |"]
    labels = {"roc_auc": "ROC AUC", "f1_score": "F1 score"}
    for row in rows:
        name = labels.get(row["metric"], row["metric"].replace("_", " ").capitalize())
        if row["ci_lower"] and row["ci_upper"]:
            values = [f"{float(row[key]):.4f}" for key in ("value", "ci_lower", "ci_upper")]
            metrics.append(f"| {name} | {' | '.join(values)} |")
        else:
            context.append(f"| {name} | {row['value']} |")
    return "\n".join(metrics) + "\n\n" + "\n".join(context)


def on_page_markdown(markdown: str, *, page: Any, config: Any, **kwargs: Any) -> str:
    """Render available result blocks, keeping placeholders for missing assets.

    Args:
        markdown: Markdown source before rendering.
        page: MkDocs page containing its source file location.
        config: MkDocs configuration containing the documentation directory.
        **kwargs: Additional MkDocs event arguments.

    Returns:
        Markdown containing available figures and metrics, or their placeholders.
    """
    page_directory = Path(config["docs_dir"]) / Path(page.file.src_uri).parent

    def render(match: re.Match[str]) -> str:
        relative_path = match["path"].strip()
        if (page_directory / relative_path).is_file():
            return f"![{match['alt'].strip()}]({relative_path})"
        return match["fallback"].strip()

    def render_metrics(match: re.Match[str]) -> str:
        path = page_directory / match["path"].strip()
        return _metrics_table(path) if path.is_file() else match["fallback"].strip()

    markdown = OPTIONAL_FIGURE.sub(render, markdown)
    return OPTIONAL_METRICS.sub(render_metrics, markdown)
