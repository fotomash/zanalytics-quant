"""Legacy FAISS-based vector storage.

This module previously supported Pinecone but now only exposes a very small
in-memory FAISS index. Remote vector database integrations should use
``BrownVectorPipeline`` from :mod:`services.vectorization_service`, which
targets Qdrant. The helpers below remain for backwards compatibility with
older enrichment utilities and tests.
"""

from __future__ import annotations

import os
from typing import Dict, Iterable, List, Optional

import numpy as np
import faiss

VECTOR_DIMENSION = int(os.getenv("VECTOR_DIMENSION", "1536"))

_faiss_index = faiss.IndexFlatL2(VECTOR_DIMENSION)
_faiss_ids: List[str] = []
_faiss_metadata: Dict[str, Dict] = {}


def add_vectors(vectors: Iterable[Iterable[float]], ids: Iterable[str], metadata: Optional[Iterable[Dict]] = None) -> None:
    """Add vectors with associated ids and metadata to the configured store."""
    if metadata is None:
        metadata = [{} for _ in ids]
    vec_array = np.array(list(vectors), dtype="float32")
    _faiss_index.add(vec_array)
    _faiss_ids.extend(list(ids))
    for id_, meta in zip(ids, metadata):
        _faiss_metadata[id_] = meta


def query_vector(vector: Iterable[float], top_k: int = 5) -> List[Dict]:
    """Return top matches for ``vector`` from the configured store."""
    if _faiss_index.ntotal == 0:
        return []
    vec = np.array([vector], dtype="float32")
    distances, indices = _faiss_index.search(vec, top_k)
    matches: List[Dict] = []
    for dist, idx in zip(distances[0], indices[0]):
        if idx == -1:
            continue
        id_ = _faiss_ids[idx]
        matches.append({"id": id_, "score": float(dist), "metadata": _faiss_metadata.get(id_)})
    return matches


__all__ = ["add_vectors", "query_vector"]
