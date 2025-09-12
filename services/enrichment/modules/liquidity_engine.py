"""Module running :class:`~core.liquidity_engine.LiquidityEngine` and updating enrichment state."""

from __future__ import annotations

from typing import Any, Dict

from core.liquidity_engine import LiquidityEngine
from enrichment.enrichment_engine import run_data_module


def run(state: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze liquidity-related structures and update ``state``.

    The function expects ``state`` to contain a ``dataframe`` key holding a
    :class:`pandas.DataFrame`.  Results from
    :meth:`LiquidityEngine.analyze` are merged back into ``state`` and the
    ``status`` flag is set to ``"PASS"`` unless critical input data is
    missing.
    """

    state = run_data_module(
        state,
        {"open", "high", "low", "close"},
        LiquidityEngine,
        "analyze",
    )
    # Ensure downstream modules relying on additional keys do not fail
    for key in ["market_structure", "liquidity_sweeps", "displacement", "inducement"]:
        state.setdefault(key, [])
    return state
