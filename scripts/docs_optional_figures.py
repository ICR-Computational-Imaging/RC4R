"""Show available figures or their existing placeholders during MkDocs builds.

Registered through ``hooks`` in mkdocs.yaml. An optional figure block starts
with ``<!-- optional-figure: relative/path.png | Figure description -->`` and
ends with ``<!-- /optional-figure -->``. Paths are relative to the source page.
The block body is the fallback Markdown shown when the figure is absent.
This hook reads documentation assets only and never runs a research pipeline.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

OPTIONAL_FIGURE = re.compile(
    r"^<!-- optional-figure: (?P<path>[^|\n]+) \| (?P<alt>[^\n]+) -->\n"
    r"(?P<fallback>.*?)^<!-- /optional-figure -->$",
    re.MULTILINE | re.DOTALL,
)


def on_page_markdown(markdown: str, *, page: Any, config: Any, **kwargs: Any) -> str:
    """Replace optional figure blocks with images when their assets exist.

    Args:
        markdown: Markdown source before rendering.
        page: MkDocs page containing its source file location.
        config: MkDocs configuration containing the documentation directory.
        **kwargs: Additional MkDocs event arguments.

    Returns:
        Markdown with images for available assets and fallbacks for missing ones.
    """
    page_directory = Path(config["docs_dir"]) / Path(page.file.src_uri).parent

    def render(match: re.Match[str]) -> str:
        relative_path = match["path"].strip()
        if (page_directory / relative_path).is_file():
            return f"![{match['alt'].strip()}]({relative_path})"
        return match["fallback"].strip()

    return OPTIONAL_FIGURE.sub(render, markdown)
