from __future__ import annotations

"""Simple semantic routing service used by tests.

The real project ships with a much richer implementation.  For the purposes of
the kata we only need a light‑weight utility that can resolve either plain text
requests or task dictionaries to a primary agent and an ordered list of
fallback agents.  The service can be initialised with an in-memory mapping or a
YAML configuration file.
"""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml


@dataclass
class MappingEntry:
    """Representation of a single text routing rule."""

    primary: str
    fallback: List[str]
    keywords: set[str]
    regex: List[re.Pattern[str]]


class SemanticMappingService:
    """Resolve tasks or text to a primary agent and fallbacks."""

    def __init__(
        self,
        mapping: Optional[Dict[str, Tuple[str, List[str]]] | str | Path] = None,
    ) -> None:
        self._direct_map: Dict[str, Tuple[str, List[str]]] = {}
        self._entries: List[MappingEntry] = []

        if isinstance(mapping, dict):
            # Mapping provided directly for task based routing
            self._direct_map = {k: (v[0], list(v[1])) for k, v in mapping.items()}
        else:
            path = Path(mapping or "mapping_interface_v2_final.yaml")
            if path.exists():
                self._load_file(path)

    # ------------------------------------------------------------------
    # Configuration loading
    # ------------------------------------------------------------------
    def _load_file(self, path: Path) -> None:
        with path.open("r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}

        for entry in data.get("mappings", []):
            triggers = entry.get("triggers", {})
            keywords = {kw.lower() for kw in triggers.get("keywords", [])}
            regex = [re.compile(pat, re.IGNORECASE) for pat in triggers.get("regex", [])]
            primary = entry.get("primary")
            fallback = list(entry.get("fallback", []))
            if primary:
                self._entries.append(MappingEntry(primary, fallback, keywords, regex))

    # ------------------------------------------------------------------
    # Routing
    # ------------------------------------------------------------------
    def route(self, request: Any) -> Tuple[Optional[str], List[str]]:
        """Return ``(primary, fallbacks)`` for ``request``.

        ``request`` may either be a plain text string or a task dictionary.
        Unmatched requests return ``(None, [])``.
        """

        # Text based routing
        if isinstance(request, str):
            tokens = set(re.findall(r"\w+", request.lower()))
            for entry in self._entries:
                if entry.keywords & tokens:
                    return entry.primary, list(entry.fallback)
                for pattern in entry.regex:
                    if pattern.search(request):
                        return entry.primary, list(entry.fallback)
            return None, []

        # Task dictionary routing
        if isinstance(request, dict):
            task_id = request.get("name") or request.get("type") or request.get("task")
            if task_id is None:
                return None, []
            primary, fallbacks = self._direct_map.get(task_id, (None, []))
            return primary, list(fallbacks)

        return None, []


__all__ = ["SemanticMappingService"]

