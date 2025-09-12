"""Tick enrichment utilities powered by the unified indicator engine.

This module loads per-stream indicator configuration, calculates
only the requested indicators using the :class:`UltimateIndicatorEngine`
and returns a lightweight dictionary suitable for Redis/Postgres storage.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Set

import numpy as np
import pandas as pd
import yaml

_ENGINE: Any | None = None


class _NullEngine:
    """Fallback engine used when the real implementation is unavailable."""

    def calculate_all_indicators(self, df: pd.DataFrame) -> Dict[str, np.ndarray]:  # pragma: no cover - simple passthrough
        return {}


def _get_indicator_engine() -> Any:
    """Return a cached instance of the unified indicator engine.

    The real engine depends on ``talib`` and other heavy scientific
    packages.  In environments where these are missing we degrade to a
    no-op engine which simply returns an empty result set.  Tests can
    monkeypatch this function to supply a stub implementation.
    """

    global _ENGINE
    if _ENGINE is None:
        try:  # pragma: no cover - exercised in tests via monkeypatching
            from utils.ncos_enhanced_analyzer import UltimateIndicatorEngine

            _ENGINE = UltimateIndicatorEngine()
        except Exception:  # pragma: no cover - fallback when deps missing
            _ENGINE = _NullEngine()
    return _ENGINE


def _load_indicator_catalog(path: str | Path) -> Dict[str, Any]:
    data = yaml.safe_load(Path(path).read_text()) or {}
    return data.get("indicators", {})


def _load_stream_overrides(stream: str, directory: str | Path) -> Dict[str, bool]:
    p = Path(directory) / f"{stream}.yaml"
    if not p.exists():
        return {}
    data = yaml.safe_load(p.read_text()) or {}
    return data.get("indicators", {})


def _resolve_enabled(stream: str, *, indicators_cfg: str | Path, stream_cfg_dir: str | Path) -> Set[str]:
    catalog = _load_indicator_catalog(indicators_cfg)
    enabled = {name for name, meta in catalog.items() if meta.get("enabled_by_default", False)}
    overrides = _load_stream_overrides(stream, stream_cfg_dir)
    for name, value in overrides.items():
        if value:
            enabled.add(name)
        else:
            enabled.discard(name)
    return enabled


def enrich_ticks(
    df: pd.DataFrame,
    stream: str,
    *,
    indicators_cfg: str | Path = "config/indicators.yml",
    stream_cfg_dir: str | Path = "config/streams",
) -> Dict[str, Dict[str, float]]:
    """Enrich ``df`` with the indicators requested for ``stream``.

    Parameters
    ----------
    df:
        DataFrame containing at least ``open``, ``high``, ``low``, ``close``
        and optionally ``volume`` columns.
    stream:
        Name of the data stream/symbol whose config should be applied.
    indicators_cfg, stream_cfg_dir:
        Locations of the indicator catalog and per-stream override files.

    Returns
    -------
    dict
        Mapping with a single ``indicators`` key whose value is a flat
        dictionary of indicator outputs.  Values are converted to native
        Python ``float`` types ensuring compatibility with Redis/Postgres
        JSON storage.
    """

    enabled = _resolve_enabled(stream, indicators_cfg=indicators_cfg, stream_cfg_dir=stream_cfg_dir)
    if not enabled:
        return {"indicators": {}}

    engine = _get_indicator_engine()
    all_indicators = engine.calculate_all_indicators(df)

    result: Dict[str, float] = {}
    for name in enabled:
        if name == "rsi":
            key = "RSI_14"
            if key in all_indicators:
                result["rsi"] = float(np.asarray(all_indicators[key])[-1])
        elif name == "macd":
            if "MACD_12_26_9" in all_indicators:
                result["macd"] = float(np.asarray(all_indicators["MACD_12_26_9"])[-1])
            if "MACD_SIGNAL_12_26_9" in all_indicators:
                result["macd_signal"] = float(np.asarray(all_indicators["MACD_SIGNAL_12_26_9"])[-1])
            if "MACD_HIST_12_26_9" in all_indicators:
                result["macd_histogram"] = float(np.asarray(all_indicators["MACD_HIST_12_26_9"])[-1])
        elif name == "bollinger_bands":
            up = all_indicators.get("BB_UPPER_20")
            mid = all_indicators.get("BB_MIDDLE_20")
            lo = all_indicators.get("BB_LOWER_20")
            if up is not None and mid is not None and lo is not None:
                result["bb_upper"] = float(np.asarray(up)[-1])
                result["bb_middle"] = float(np.asarray(mid)[-1])
                result["bb_lower"] = float(np.asarray(lo)[-1])

    return {"indicators": result}


__all__ = ["enrich_ticks"]
