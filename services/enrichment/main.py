"""Entrypoint for running the enrichment pipeline orchestrator."""

from __future__ import annotations

from typing import Any, Dict, Optional

from pipeline import run as run_pipeline
from utils.enrichment_config import load_enrichment_config


def main(
    dataframe: Any,
    metadata: Dict[str, Any],
    configs: Optional[Dict[str, Dict[str, Any]]] = None,
    config_path: str = "config/enrichment_default.yaml",
) -> Dict[str, Any]:
    """Execute the enrichment pipeline and return its final state.

    Configuration is loaded from ``config_path`` and validated using
    :class:`~utils.enrichment_config.EnrichmentConfig`.  To enable harmonic
    pattern enrichment with vector database persistence, pass
    ``config/enrichment_harmonic.yaml``.  Any configs passed explicitly will
    override the defaults.
    """

    base_cfg = load_enrichment_config(config_path).to_module_configs()
    if configs:
        base_cfg.update(configs)
    return run_pipeline(dataframe, metadata, base_cfg)


__all__ = ["main"]
