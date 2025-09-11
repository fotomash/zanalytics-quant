"""Confidence tracing utilities.

This module loads scoring matrices and strategy rules to produce a
normalised confidence score for agent outputs.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, Tuple


class ConfidenceTracer:
    """Derive a confidence score from an agent result.

    The tracer consults ``confidence_trace_matrix.json`` for per-agent
    simulation adjustments and normalisation factors, and
    ``config/strategy_rules.json`` for contextual weighting based on
    strategy names present in the result.
    """

    def __init__(self) -> None:
        base_path = Path(__file__).resolve().parent.parent
        matrix_path = base_path / "confidence_trace_matrix.json"
        rules_path = base_path / "config" / "strategy_rules.json"

        try:
            with matrix_path.open("r", encoding="utf-8") as fh:
                self.matrix: Dict[str, Dict[str, float]] = json.load(fh)
        except FileNotFoundError:
            self.matrix = {}

        try:
            with rules_path.open("r", encoding="utf-8") as fh:
                rules = json.load(fh)
        except FileNotFoundError:
            rules = {"strategies": []}

        # Pre-compute simple weights based on number of conditions.
        self.strategy_weights: Dict[str, float] = {}
        for strategy in rules.get("strategies", []):
            conditions = strategy.get("conditions", [])
            # Each condition adds a small weighting.
            self.strategy_weights[strategy.get("name", "")] = 1.0 + 0.1 * len(conditions)

    def trace(self, agent_name: str, result: Dict[str, Any]) -> Tuple[float, Dict[str, float]]:
        """Return a confidence score and debug info.

        Parameters
        ----------
        agent_name:
            Name of the agent producing ``result``.
        result:
            Mapping containing at least ``raw_calculation`` from the agent
            and optionally a ``strategy`` name.
        """

        raw = float(result.get("raw_calculation", 0.0))
        logging.debug("raw_calculation for %s: %s", agent_name, raw)

        matrix_values = self.matrix.get(agent_name, {})
        sim_adj = float(matrix_values.get("simulation_adjustment", 0.0))
        norm = float(matrix_values.get("normalization", 1.0))
        adjusted = (raw + sim_adj) / norm if norm else 0.0

        strategy_name = result.get("strategy", "")
        weight = self.strategy_weights.get(strategy_name, 1.0)

        final = max(0.0, min(adjusted * weight, 1.0))

        debug = {
            "raw": raw,
            "simulation_adjustment": sim_adj,
            "normalization": norm,
            "strategy_weight": weight,
            "final": final,
        }
        logging.debug("Confidence trace for %s: %s", agent_name, debug)

        return final, debug


__all__ = ["ConfidenceTracer"]
