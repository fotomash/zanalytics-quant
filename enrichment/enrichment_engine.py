"""Shared utilities for enrichment modules.

This module centralizes common routines used by multiple enrichment
modules. It provides helpers for validating the presence of a DataFrame
in the shared ``state`` dictionary and for executing core analytic engines
while updating the state consistently.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, Callable

import pandas as pd


def ensure_dataframe(state: Dict[str, Any], required_cols: Iterable[str] | None = None) -> pd.DataFrame | None:
    """Return a valid DataFrame from ``state`` or mark failure.

    Parameters
    ----------
    state:
        Mutable state dictionary expected to contain a ``dataframe`` key.
    required_cols:
        Optional iterable of column names that must be present in the
        DataFrame. If validation fails, ``state['status']`` is set to
        ``"FAIL"`` and ``None`` is returned.
    """
    df = state.get("dataframe")
    if not isinstance(df, pd.DataFrame):
        state["status"] = "FAIL"
        return None
    if required_cols and not set(required_cols).issubset(df.columns):
        state["status"] = "FAIL"
        return None
    return df


def run_data_module(
    state: Dict[str, Any],
    required_cols: Iterable[str],
    engine_factory: Callable[[], Any],
    method: str = "analyze",
) -> Dict[str, Any]:
    """Execute an engine method with DataFrame validation.

    This helper encapsulates the common pattern used across enrichment
    modules: fetch and validate the DataFrame from ``state``, run the
    provided ``engine`` method, merge the resulting dictionary back into
    ``state`` and mark execution status.
    """
    df = ensure_dataframe(state, required_cols)
    if df is None:
        return state
    engine = engine_factory()
    results = getattr(engine, method)(df)
    if isinstance(results, dict):
        state.update(results)
    state["status"] = "PASS"
    return state


def run_state_module(
    state: Dict[str, Any],
    engine_factory: Callable[[], Any],
    method: str = "score",
) -> Dict[str, Any]:
    """Execute an engine method that operates directly on ``state``.

    Unlike :func:`run_data_module` this helper does not validate or pass a
    DataFrame. The provided ``engine`` method receives ``state`` and may
    mutate it directly or return a dictionary of results to be merged.
    """
    engine = engine_factory()
    results = getattr(engine, method)(state)
    if isinstance(results, dict):
        state.update(results)
    state.setdefault("status", "PASS")
    return state


__all__ = ["ensure_dataframe", "run_data_module", "run_state_module"]
