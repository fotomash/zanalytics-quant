"""Routing service based on semantic mappings.

The service loads a YAML configuration file named
``mapping_interface_v2_final.yaml`` on startup. Each entry in the
configuration defines a set of keyword or regular expression triggers that
map to a primary agent and optional fallback agents.

Example YAML structure::

    mappings:
      - primary: agent_a
        fallback: [agent_b, agent_c]
        triggers:
          keywords: [hello, hi]
          regex: ["foo.*bar"]

```SemanticMappingService.route``` returns the first matching mapping for the
provided text.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import List, Optional, Tuple

import yaml


@dataclass
class MappingEntry:
    """Represents a single mapping rule."""

    primary: str
    fallback: List[str]
    keywords: set[str]
    regex: List[re.Pattern[str]]


class SemanticMappingService:
    """Route text requests to agents using keyword or regex triggers."""

    def __init__(self, mapping_file: str | Path | None = None) -> None:
        base_dir = Path(__file__).resolve().parent.parent
        self.mapping_file = (
            Path(mapping_file)
            if mapping_file is not None
            else base_dir / "mapping_interface_v2_final.yaml"
        )
        self.mappings: List[MappingEntry] = []
        self._load_mappings()

    def _load_mappings(self) -> None:
        if not self.mapping_file.exists():
            return
        with self.mapping_file.open("r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
        for entry in data.get("mappings", []):
            triggers = entry.get("triggers", {})
            keywords = {kw.lower() for kw in triggers.get("keywords", [])}
            regex = [re.compile(pattern) for pattern in triggers.get("regex", [])]
            self.mappings.append(
                MappingEntry(
                    primary=entry.get("primary"),
                    fallback=list(entry.get("fallback", [])),
                    keywords=keywords,
                    regex=regex,
                )
            )

    def route(self, request_text: str) -> Tuple[Optional[str], List[str]]:
        """Return the primary agent and fallbacks for ``request_text``.

        The first mapping whose keywords or regex patterns match is returned.
        If no mapping matches, ``(None, [])`` is returned.
        """

        text_lower = request_text.lower()
        tokens = set(re.findall(r"\w+", text_lower))
        for mapping in self.mappings:
            if mapping.keywords & tokens:
                return mapping.primary, mapping.fallback
            for pattern in mapping.regex:
                if pattern.search(request_text):
                    return mapping.primary, mapping.fallback
        return None, []
