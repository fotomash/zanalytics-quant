"""Core market analyzers for confluence scoring."""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

try:
    from smartmoneyconcepts import smc
except Exception:  # pragma: no cover - dependency missing
    smc = None


def detect_wyckoff_patterns(df: pd.DataFrame) -> Optional[Dict[str, object]]:
    """Detect a basic head and shoulders pattern as Wyckoff proxy.

    Parameters
    ----------
    df : pd.DataFrame
        Data with at least ``high`` column.
    """
    if len(df) < 3:
        return None
    highs = df["high"].values
    for i in range(1, len(highs) - 1):
        left, mid, right = highs[i - 1], highs[i], highs[i + 1]
        if mid > left and mid > right and abs(left - right) / max(left, right) < 0.1:
            strength = (mid - max(left, right)) / mid * 100
            return {
                "pattern": "head_and_shoulders",
                "strength": round(float(strength), 2),
                "reasons": ["Wyckoff BOS detected"],
            }
    return None


def detect_smc(df: pd.DataFrame) -> Optional[Dict[str, object]]:
    """Detect Smart Money Concepts features like BOS/CHOCH and FVG."""
    if smc is None:
        return None
    work = df.copy()
    work.columns = work.columns.str.lower()
    swing = smc.swing_highs_lows(work, swing_length=2)
    bos = smc.bos_choch(work, swing, close_break=True)
    fvg = smc.fvg(work)
    imbalance = float(fvg["FVG"].fillna(0).max())
    reasons: List[str] = []
    if (bos["BOS"].fillna(0) != 0).any():
        reasons.append("SMC BOS/CHOCH")
    if imbalance:
        reasons.append("Liquidity imbalance (FVG)")
    if reasons:
        return {"imbalance": imbalance, "reasons": reasons}
    return None


def compute_confluence(df: pd.DataFrame, weights_path: str = "config/confluence_weights.json") -> Dict[str, object]:
    """Compute overall confluence score from analyzers."""
    import json

    weights = {"Wyckoff": 0.3, "SMC": 0.5}
    path = Path(weights_path)
    if path.exists():
        with path.open() as fh:
            weights.update(json.load(fh))

    score = 0.0
    reasons: List[str] = []

    wyckoff = detect_wyckoff_patterns(df)
    if wyckoff:
        score += wyckoff["strength"] * weights.get("Wyckoff", 0)
        reasons.extend(wyckoff["reasons"])

    smc_res = detect_smc(df)
    if smc_res:
        score += smc_res["imbalance"] * 100 * weights.get("SMC", 0)
        reasons.extend(smc_res["reasons"])

    grade = "High" if score > 80 else "Medium" if score > 50 else "Low"
    return {"score": int(score), "grade": grade, "reasons": reasons}
