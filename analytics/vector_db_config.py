"""Vector database configuration supporting Pinecone and local FAISS."""

from __future__ import annotations

import os
from typing import Dict, Iterable, List, Optional

import numpy as np

PINECONE_URL = os.getenv("PINECONE_URL", "")
USE_LOCAL = PINECONE_URL == "https://localhost:443"

INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "analytics-index")
VECTOR_DIMENSION = int(os.getenv("VECTOR_DIMENSION", "1536"))

if USE_LOCAL:
    import faiss

    _faiss_index = faiss.IndexFlatL2(VECTOR_DIMENSION)
    _faiss_ids: List[str] = []
    _faiss_metadata: Dict[str, Dict] = {}
else:  # pragma: no cover - exercised via test double
    import pinecone

    PINECONE_API_KEY = os.getenv("PINECONE_API_KEY", "")
    PINECONE_ENVIRONMENT = os.getenv("PINECONE_ENVIRONMENT", os.getenv("PINECONE_ENV"))
    pinecone.init(api_key=PINECONE_API_KEY, environment=PINECONE_ENVIRONMENT)
    if INDEX_NAME not in pinecone.list_indexes():
        pinecone.create_index(INDEX_NAME, dimension=VECTOR_DIMENSION)
    _pinecone_index = pinecone.Index(INDEX_NAME)


def add_vectors(vectors: Iterable[Iterable[float]], ids: Iterable[str], metadata: Optional[Iterable[Dict]] = None) -> None:
    """Add vectors with associated ids and metadata to the configured store."""
    if metadata is None:
        metadata = [{} for _ in ids]
    if USE_LOCAL:
        vec_array = np.array(list(vectors), dtype="float32")
        _faiss_index.add(vec_array)
        _faiss_ids.extend(list(ids))
        for id_, meta in zip(ids, metadata):
            _faiss_metadata[id_] = meta
    else:  # pragma: no cover - exercised via test double
        payload = list(zip(ids, vectors, metadata))
        _pinecone_index.upsert(vectors=payload)


def query_vector(vector: Iterable[float], top_k: int = 5) -> List[Dict]:
    """Return top matches for ``vector`` from the configured store."""
    if USE_LOCAL:
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
    # pragma: no cover - exercised via test double
    result = _pinecone_index.query(vector=vector, top_k=top_k, include_metadata=True)
    return [
        {"id": m.id, "score": m.score, "metadata": getattr(m, "metadata", None)}
        for m in result.matches
    ]


__all__ = ["add_vectors", "query_vector", "USE_LOCAL"]
