import os
import re
from typing import List, Optional, Tuple

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
from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import yaml


class SemanticMappingService:
    """Service that routes text to agents based on semantic mappings.

    The mappings are defined in a YAML file with the following structure::

        mappings:
          - triggers:
              keywords: ["balance", "equity"]
              regex: ["account\\s+info"]
            primary: balance_agent
            fallback: [general_agent]

    """

    def __init__(self, mapping_file: Optional[str] = None) -> None:
        if mapping_file is None:
            mapping_file = os.path.join(
                os.path.dirname(__file__), "..", "mapping_interface_v2_final.yaml"
            )
            mapping_file = os.path.abspath(mapping_file)
        self._load_mappings(mapping_file)

    # Internal helpers -------------------------------------------------
    def _load_mappings(self, path: str) -> None:
        with open(path, "r", encoding="utf-8") as fh:
            raw_cfg = yaml.safe_load(fh) or {}

        self.mappings = []
        for item in raw_cfg.get("mappings", []):
            triggers = item.get("triggers", {})
            keywords = [kw.lower() for kw in triggers.get("keywords", [])]
            regex_patterns = [re.compile(r) for r in triggers.get("regex", [])]
            primary = item.get("primary") or item.get("primary_agent")
            fallback = item.get("fallback") or item.get("fallback_agents") or []

            self.mappings.append(
                {
                    "keywords": keywords,
                    "regex": regex_patterns,
                    "primary": primary,
                    "fallback": list(fallback),
                }
            )

    # Public API -------------------------------------------------------
    def route(self, request_text: str) -> Tuple[Optional[str], List[str]]:
        """Return the appropriate agents for *request_text*.

        Parameters
        ----------
        request_text:
            User supplied text.
=======
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
            ``(primary_agent, fallback_agents)``. ``primary_agent`` is ``None``
            when no mapping matched ``request_text``.
        """

        text = request_text.lower()
        for mapping in self.mappings:
            matched = False
            for keyword in mapping["keywords"]:
                if keyword in text:
                    matched = True
                    break
            if not matched:
                for pattern in mapping["regex"]:
                    if pattern.search(request_text):
                        matched = True
                        break
            if matched:
                return mapping["primary"], mapping["fallback"]
        return None, []
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
