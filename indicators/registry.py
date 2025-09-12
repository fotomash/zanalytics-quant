"""Lightweight indicator registry.

This module enumerates available indicator names and their high level
categories.  Analyzers register the features they expose here on
initialization which allows tests or downstream consumers to enable or
disable indicators dynamically.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List


@dataclass
class IndicatorSpec:
    """Specification for a single indicator."""

    category: str
    enabled: bool = True


#: Global registry mapping indicator name to its specification
INDICATORS: Dict[str, IndicatorSpec] = {
    # SMC features
    "liquidity_zones": IndicatorSpec("liquidity"),
    "order_blocks": IndicatorSpec("structure"),
    "fair_value_gaps": IndicatorSpec("imbalance"),
    "market_structure": IndicatorSpec("structure"),
    "liquidity_sweeps": IndicatorSpec("liquidity"),
    "displacement": IndicatorSpec("momentum"),
    "inducement": IndicatorSpec("liquidity"),
    # Wyckoff/Context features
    "current_phase": IndicatorSpec("wyckoff"),
    "events": IndicatorSpec("wyckoff"),
    "volume_analysis": IndicatorSpec("volume"),
    "spring_upthrust": IndicatorSpec("wyckoff"),
    "sos_sow": IndicatorSpec("wyckoff"),
    "trading_ranges": IndicatorSpec("wyckoff"),
    "composite_operator": IndicatorSpec("volume"),
    # Context analyzer short names
    "phase": IndicatorSpec("context"),
}


def register_indicator(name: str, category: str) -> None:
    """Register *name* with *category* if not already present."""

    INDICATORS.setdefault(name, IndicatorSpec(category))


def enable_indicator(name: str) -> None:
    """Enable an indicator if it exists in the registry."""

    spec = INDICATORS.get(name)
    if spec:
        spec.enabled = True


def disable_indicator(name: str) -> None:
    """Disable an indicator if it exists in the registry."""

    spec = INDICATORS.get(name)
    if spec:
        spec.enabled = False


def set_enabled(selected: Iterable[str]) -> None:
    """Enable only indicators listed in *selected* and disable others."""

    selected_set = set(selected)
    for name, spec in INDICATORS.items():
        spec.enabled = name in selected_set


def is_indicator_enabled(name: str) -> bool:
    """Return whether *name* is enabled."""

    spec = INDICATORS.get(name)
    return bool(spec and spec.enabled)


def enabled_indicators(category: str | None = None) -> List[str]:
    """Return all enabled indicator names optionally filtered by *category*."""

    return [
        name
        for name, spec in INDICATORS.items()
        if spec.enabled and (category is None or spec.category == category)
    ]


__all__ = [
    "IndicatorSpec",
    "INDICATORS",
    "register_indicator",
    "enable_indicator",
    "disable_indicator",
    "set_enabled",
    "is_indicator_enabled",
    "enabled_indicators",
]

