"""Entrypoint for running the enrichment pipeline."""

from __future__ import annotations

from typing import Any, Dict, Optional

from .pipeline import run as run_pipeline


def main(
    dataframe: Any,
    metadata: Dict[str, Any],
    configs: Optional[Dict[str, Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Execute the enrichment pipeline with the given inputs."""

    return run_pipeline(dataframe, metadata, configs or {})


__all__ = ["main"]
