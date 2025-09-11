"""Helpers for loading markdown documentation."""

from __future__ import annotations

from pathlib import Path
from typing import Dict


def load_markdown_docs(directory: str | Path = "docs") -> Dict[str, str]:
    """Load all markdown files from ``directory``.

    Parameters
    ----------
    directory:
        Folder containing ``.md`` files.

    Returns
    -------
    dict
        Mapping of filename stem to markdown content.
    """
    docs: Dict[str, str] = {}
    path = Path(directory)
    for md_file in path.glob("*.md"):
        with md_file.open("r", encoding="utf-8") as fh:
            docs[md_file.stem] = fh.read()
    return docs
