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

