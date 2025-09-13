"""Detect harmonic price patterns and optionally upload vectors to Qdrant."""

from __future__ import annotations

import asyncio
import os
from typing import Any, Dict, List

from qdrant_client import QdrantClient

from core.harmonic_processor import HarmonicProcessor as PatternAnalyzer
from enrichment.enrichment_engine import run_data_module
from services.mcp2.vector.embeddings import embed




def run(state: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    """Populate ``state`` with harmonic pattern analysis and upload vectors."""


    state = run_data_module(
        state,
        required_cols=("open", "high", "low", "close"),
        engine_factory=lambda: PatternAnalyzer(**config),
    )
    if state.get("status") != "FAIL":
        harmonic = state.get("harmonic")
        if isinstance(harmonic, HarmonicResult):
            harmonic_dict = harmonic.model_dump()
        elif isinstance(harmonic, dict):
            harmonic_dict = harmonic
        else:
            harmonic_dict = {}
        state["harmonic"] = harmonic_dict
        state["HarmonicProcessor"] = harmonic_dict
    return state

    if not config.get("upload"):
        return state

    patterns: List[Dict[str, Any]] = state.get("harmonic_patterns", [])
    if not patterns:
        return state

    vectors = [embed(_pattern_to_text(p)) for p in patterns]
    payloads = [{k: v for k, v in p.items() if k != "points"} for p in patterns]
    ids = list(range(len(patterns)))

    url = os.getenv("QDRANT_URL", "http://localhost:6333")
    api_key = os.getenv("QDRANT_API_KEY")
    client = QdrantClient(url=url, api_key=api_key)
    uploader = QdrantUploader(client, collection_name=config.get("collection", "harmonic"))

    async def _upsert() -> None:
        await uploader.upsert(vectors, payloads, ids)

    asyncio.run(_upsert())
    return state


__all__ = ["run"]

