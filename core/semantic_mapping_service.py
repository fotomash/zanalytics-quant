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

"""Lightweight semantic mapping service.

The real project ships with a fairly feature rich implementation.  For the
purposes of the kata and unit tests we only implement a tiny subset of the
behaviour.  The service can read agent routing metadata from the agent
registry and use simple keyword matching to resolve a request to a primary
agent and optional fallbacks.

The module also exposes a trivial static :func:`route` method used by the
``BootstrapEngine`` for confidence based fallbacks.  Tests may monkey‑patch
this static method as required.
"""

import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml


class SemanticMappingService:
    """Resolve text requests to agents using routing hints.

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
    registry:
        Optional registry mapping agent identifiers to objects containing a
        ``path`` attribute pointing at the agent's YAML configuration.  The
        YAML file may include a ``routing`` section with ``primary``,
        ``fallback`` and ``hints.keywords`` fields.
    """

    def __init__(self, registry: Optional[Dict[str, Any]] = None) -> None:
        self.keyword_map: Dict[str, Tuple[str, List[str]]] = {}
        if registry:
            self._load_registry(registry)

    # ------------------------------------------------------------------
    # Registry loading
    # ------------------------------------------------------------------
    def _load_registry(self, registry: Dict[str, Any]) -> None:
        for agent_id, spec in registry.items():
            path = getattr(spec, "path", None)
            if path is None and isinstance(spec, dict):
                path = spec.get("path")
            if path is None:
                continue
            try:
                with Path(path).open("r", encoding="utf-8") as fh:
                    data = yaml.safe_load(fh) or {}
            except FileNotFoundError:  # pragma: no cover - defensive
                continue
            agent_cfg = data.get("agent", {})
            routing = agent_cfg.get("routing", {})
            if not routing.get("primary"):
                continue
            fallbacks = routing.get("fallback", []) or []
            hints = routing.get("hints", {})
            keywords: List[str]
            if isinstance(hints, dict):
                keywords = list(hints.get("keywords", []) or [])
            else:
                keywords = list(hints or [])
            for kw in keywords:
                self.keyword_map[kw.lower()] = (agent_id, list(fallbacks))

    # ------------------------------------------------------------------
    # Resolution API
    # ------------------------------------------------------------------
    def resolve(self, text: str) -> Tuple[Optional[str], List[str]]:
        """Return ``(primary, fallbacks)`` for ``text``.

        Matching is case insensitive and based on simple token membership.
        ``None`` is returned when no keyword matches.
        """

        tokens = set(re.findall(r"\b\w+\b", text.lower()))
        for keyword, mapping in self.keyword_map.items():
            if keyword in tokens:
                return mapping
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

    # ------------------------------------------------------------------
    # Fallback stub used by ``BootstrapEngine``
    # ------------------------------------------------------------------
    @staticmethod
    def route(agent_id: str) -> List[str]:  # pragma: no cover - trivial
        """Return fallbacks for ``agent_id``.

        The default implementation returns an empty list.  Tests may
        monkey‑patch this method to provide custom behaviour.
        """

        return []


__all__ = ["SemanticMappingService"]

