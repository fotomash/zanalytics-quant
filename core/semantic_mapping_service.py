"""Semantic request routing utilities.

This module exposes :class:`SemanticMappingService` which loads a YAML
configuration describing keyword and regular-expression triggers for a set of
agents.  Incoming text requests can then be routed to the appropriate primary
agent with a list of fallbacks.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import yaml


class SemanticMappingService:
    """Routes requests to agents based on a semantic mapping configuration.

    The service loads a YAML file at start-up which defines trigger rules
    (keywords or regular expressions) and the corresponding primary and
    fallback agents. The configuration is expected to have the following
    structure::

        mappings:
          - primary: agent_name
            fallback: [fallback_agent1, fallback_agent2]
            triggers:
              keywords: [keyword1, keyword2]
              regex: ["^pattern$"]

    Parameters
    ----------
    mapping_path:
        Optional path to the YAML mapping file. If not provided the service
        looks for ``mapping_interface_v2_final.yaml`` in the current working
        directory.
    """

    def __init__(self, mapping_path: Optional[str] = None) -> None:
        self.mapping_path = Path(mapping_path or "mapping_interface_v2_final.yaml")
        self.keyword_map: Dict[str, Tuple[str, List[str]]] = {}
        self.regex_map: List[Tuple[re.Pattern[str], str, List[str]]] = []
        self._load_mappings()

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------
    def _load_mappings(self) -> None:
        """Load and parse the YAML mapping file."""

        if not self.mapping_path.exists():
            raise FileNotFoundError(f"Mapping file not found: {self.mapping_path}")

        with self.mapping_path.open("r", encoding="utf-8") as fh:
            config = yaml.safe_load(fh) or {}

        for entry in config.get("mappings", []):
            primary = entry.get("primary")
            fallback = entry.get("fallback", []) or []
            triggers = entry.get("triggers", {})

            for keyword in triggers.get("keywords", []) or []:
                # Store keywords in lowercase for case-insensitive matching
                self.keyword_map[keyword.lower()] = (primary, list(fallback))

            for pattern in triggers.get("regex", []) or []:
                self.regex_map.append(
                    (re.compile(pattern, re.IGNORECASE), primary, list(fallback))
                )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def route(self, request_text: str) -> Tuple[Optional[str], List[str]]:
        """Route a request to the appropriate agents.

        The method first attempts keyword based matching. If no keyword matches,
        regular expression rules are evaluated. If no rules match,
        ``(None, [])`` is returned.
        """

        text = request_text.lower()
        tokens = set(re.findall(r"\b\w+\b", text))

        for keyword, mapping in self.keyword_map.items():
            if keyword in tokens:
                return mapping

        for pattern, primary, fallback in self.regex_map:
            if pattern.search(request_text):
                return primary, fallback

        return None, []


__all__ = ["SemanticMappingService"]

