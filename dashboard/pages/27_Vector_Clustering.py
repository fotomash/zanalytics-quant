"""Vector clustering explorer using embeddings from Qdrant collections."""

from __future__ import annotations

import os
from typing import Any, Dict, List

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

try:  # qdrant-client is optional at runtime
    from qdrant_client import QdrantClient
except Exception:  # pragma: no cover - optional dependency
    QdrantClient = None  # type: ignore

from utils.enrich import get_embedding
from dashboard.utils.streamlit_api import apply_custom_styling


st.set_page_config(page_title="Vector Clustering", page_icon="🧬", layout="wide")
apply_custom_styling()
st.title("Vector Clustering")

_DATASETS = ["harmonic_patterns", "smc_vectors", "dss_vectors"]
_dataset = st.selectbox("Dataset", _DATASETS)
_method = st.selectbox("Dimensionality reduction", ["UMAP", "t-SNE"])
_limit = st.slider("Max points", 100, 2000, 500, step=100)


@st.cache_data(show_spinner=False)
def _fetch_vectors(collection: str, limit: int) -> pd.DataFrame:
    if QdrantClient is None:
        st.error("qdrant-client not installed")
        return pd.DataFrame()
    url = os.getenv("QDRANT_URL", "http://localhost:6333")
    api_key = os.getenv("QDRANT_API_KEY")
    try:
        client = QdrantClient(url=url, api_key=api_key)
        points, _ = client.scroll(
            collection_name=collection,
            limit=limit,
            with_vectors=True,
            with_payload=True,
        )
    except Exception as exc:  # pragma: no cover - network side effects
        st.error(f"Qdrant connection failed: {exc}")
        return pd.DataFrame()

    rows: List[Dict[str, Any]] = []
    for p in points:
        vec = p.vector or get_embedding(str(p.id))
        if vec is None:
            continue
        payload = p.payload or {}
        pattern = (
            payload.get("pattern")
            or payload.get("pattern_type")
            or payload.get("type")
            or payload.get("label")
            or "unknown"
        )
        conf = payload.get("confluence") or payload.get("confidence")
        rows.append({"vector": vec, "pattern": pattern, "confidence": conf})
    return pd.DataFrame(rows)


df = _fetch_vectors(_dataset, _limit)
if df.empty:
    st.warning("No vectors retrieved.")
else:
    vectors = np.vstack(df["vector"].to_numpy())
    if _method == "UMAP":
        try:  # optional dependency
            import umap  # type: ignore

            reducer = umap.UMAP(n_components=2, random_state=42)
        except Exception as exc:  # pragma: no cover - optional dependency
            st.error(f"UMAP unavailable: {exc}")
            st.stop()
    else:
        from sklearn.manifold import TSNE

        reducer = TSNE(
            n_components=2, random_state=42, init="random", learning_rate="auto"
        )
    coords = reducer.fit_transform(vectors)
    df["x"], df["y"] = coords[:, 0], coords[:, 1]
    fig = px.scatter(
        df,
        x="x",
        y="y",
        color="confidence",
        symbol="pattern",
        hover_data=["pattern", "confidence"],
    )
    st.plotly_chart(fig, use_container_width=True)
