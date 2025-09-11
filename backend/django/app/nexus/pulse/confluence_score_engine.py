"""
Lightweight confluence scoring engine for Pulse gates.

Purpose
-------
Centralize logic that converts a set of gate results into a single
confluence score that other components (services, UIs, agents) can use.

This module is intentionally framework-agnostic and has no Django/Streamlit
dependencies so it can be imported from web services, workers, or tests.
"""

from __future__ import annotations

from typing import Dict, Any, Tuple


def compute_confluence_score(
    gate_outputs: Dict[str, Dict[str, Any]],
    weights: Dict[str, float],
    threshold: float = 0.6,
) -> Tuple[float, Dict[str, Any]]:
    """
    Compute a normalized confluence score in [0.0, 1.0].

    Args
    ----
    gate_outputs: mapping of gate_name -> {"passed": bool, ...}
        Example: {
            "structure": {"passed": True},
            "liquidity": {"passed": False},
            "risk":      {"passed": True},
        }
    weights: mapping of gate_name -> weight (>= 0)
        Example: {"structure": 0.4, "liquidity": 0.3, "risk": 0.3}
    threshold: pass threshold for resulting score (0.0–1.0)

    Returns
    -------
    (score, details)
        score: float in [0.0, 1.0]
        details: dict with per-gate reasons and summary keys:
            - gate_name: "passed" | "failed" | "missing"
            - score_passed: bool
            - score_percent: float 0–100
    """
    if not isinstance(gate_outputs, dict):
        gate_outputs = {}
    if not isinstance(weights, dict):
        weights = {}

    # Only consider non-negative weights
    weights = {k: float(v) for k, v in weights.items() if isinstance(v, (int, float)) and v >= 0}
    total_weight = sum(weights.values()) or 1.0  # avoid div-by-zero

    score = 0.0
    reasons: Dict[str, Any] = {}

    for gate, weight in weights.items():
        result = gate_outputs.get(gate)
        if not isinstance(result, dict):
            reasons[gate] = "missing"
            continue
        passed = bool(result.get("passed", False))
        if passed:
            score += weight
            reasons[gate] = "passed"
        else:
            reasons[gate] = "failed"

    score_normalized = score / total_weight
    reasons["score_passed"] = score_normalized >= float(threshold)
    reasons["score_percent"] = round(score_normalized * 100.0, 2)

    return score_normalized, reasons


__all__ = ["compute_confluence_score"]

