"""Wrapper around :mod:`components.wyckoff_analyzer`.

This module exposes :class:`WyckoffAnalyzer` from :mod:`components` in the
``core`` namespace to provide a stable import path for services.
"""

from __future__ import annotations

from typing import Any, Optional

from components.wyckoff_analyzer import WyckoffAnalyzer as _BaseWyckoffAnalyzer


class WyckoffAnalyzer(_BaseWyckoffAnalyzer):
    """Bridge class accepting optional configuration."""

    def __init__(self, config: Optional[dict[str, Any]] = None) -> None:
        super().__init__()
        self.config = config or {}

