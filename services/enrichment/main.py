"""Entrypoint for running the enrichment pipeline orchestrator."""

from __future__ import annotations

from typing import Any, Dict, Optional

from .pipeline import run as run_pipeline


def main(
    dataframe: Any,
    metadata: Dict[str, Any],
    configs: Optional[Dict[str, Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Execute the enrichment pipeline and return its final state."""

    return run_pipeline(dataframe, metadata, configs or {})


__all__ = ["main"]
