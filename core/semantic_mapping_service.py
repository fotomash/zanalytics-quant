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

    def _load_mappings(self) -> None:
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

    def route(self, request_text: str) -> Tuple[Optional[str], List[str]]:
        """Route a request to the appropriate agents.

        The method first attempts keyword based matching. If no keyword matches,
        regular expression rules are evaluated. If no rules match, ``(None, [])``
        is returned.
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
from typing import Any, Dict, List, Optional, Tuple


class SemanticMappingService:
    """Resolve tasks to their primary and fallback agents.

    The service maintains a simple mapping between a task identifier and
    the agent that should handle it.  Tasks are expected to be ``dict``
    objects containing at least a ``name``/``type``/``task`` key.  The
    mapping returns a tuple consisting of the primary agent identifier and
    a list of fallback agent identifiers.
    """

    def __init__(
        self,
        mapping: Optional[Dict[str, Tuple[str, List[str]]]] = None,
    ) -> None:
        self.mapping: Dict[str, Tuple[str, List[str]]] = mapping or {}

    def route(self, task: Dict[str, Any]) -> Tuple[Optional[str], List[str]]:
        """Return the primary agent and fallbacks for ``task``.

        Parameters
        ----------
        task:
            Arbitrary task description.  The service attempts to extract a
            task identifier from the ``name``, ``type`` or ``task`` fields.

        Returns
        -------
        tuple
            ``(primary, fallbacks)`` where ``primary`` may be ``None`` when
            no mapping exists.
        """

        task_id = (
            task.get("name")
            or task.get("type")
            or task.get("task")
        )
        if task_id is None:
            return None, []
        primary, fallbacks = self.mapping.get(task_id, (None, []))
        return primary, list(fallbacks)

"""Simple semantic routing utilities.

The real project contains a service responsible for determining which
fallback agents should handle a request when the primary agent's
confidence score is insufficient.  For the purposes of the unit tests in
this kata the service provides a minimal stub with a single ``route``
method that may be monkey‑patched by tests.
"""
from __future__ import annotations

from typing import List


class SemanticMappingService:
    """Return fallback agent identifiers for a given primary agent."""

    @staticmethod
    def route(agent_id: str) -> List[str]:  # pragma: no cover - trivial
        """Return an ordered list of fallback agent identifiers.

        The default implementation returns an empty list.  Unit tests
        typically patch this method to supply custom routing behaviour.
        """

        return []


__all__ = ["SemanticMappingService"]
