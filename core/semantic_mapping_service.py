from __future__ import annotations
"""Semantic request routing utilities.

This module exposes :class:`SemanticMappingService` which loads a YAML
configuration describing keyword and regular-expression triggers for a set of
agents.  Incoming text requests can then be routed to the appropriate primary
agent with a list of fallbacks.
"""


import os
import re
from typing import List, Optional, Tuple

"""Routing service based on semantic mappings.

The service loads a YAML configuration file named
``mapping_interface_v2_final.yaml`` on startup. Each entry in the
configuration defines a set of keyword or regular expression triggers that
map to a primary agent and optional fallback agents.

Example YAML structure::

"""Simple semantic routing service used by tests.

The real project ships with a much richer implementation.  For the purposes of
the kata we only need a light‑weight utility that can resolve either plain text
requests or task dictionaries to a primary agent and an ordered list of
fallback agents.  The service can be initialised with an in-memory mapping or a
YAML configuration file.
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
from dataclasses import dataclass
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

        return None, []


__all__ = ["SemanticMappingService"]

