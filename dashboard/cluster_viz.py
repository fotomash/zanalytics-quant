"""Streamlit dashboard for visualizing enriched vector clusters."""

from __future__ import annotations

import asyncio
from typing import Iterable

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st
from sklearn.manifold import TSNE

try:
    import umap  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    umap = None

from services.mcp2.llm_calls import call_whisperer


def load_enriched_vectors(num_vectors: int = 200, dim: int = 50) -> pd.DataFrame:
    """Return a DataFrame of mock enriched vectors.

    In a production environment these vectors would be pulled from the
    enrichment pipeline or a dedicated vector store. For demonstration
    purposes we generate deterministic random vectors.
    """

    rng = np.random.default_rng(42)
    vectors = rng.normal(size=(num_vectors, dim))
    ids = [f"vec_{i}" for i in range(num_vectors)]
    return pd.DataFrame({"id": ids, "vector": list(vectors)})


def reduce_vectors(vectors: Iterable[Iterable[float]], method: str) -> np.ndarray:
    """Project vectors to 2D using ``method`` (``umap`` or ``tsne``)."""

    array = np.vstack(list(vectors))
    if method == "umap" and umap is not None:
        reducer = umap.UMAP(n_components=2, random_state=42)
        return reducer.fit_transform(array)
    # Fall back to t-SNE
    tsne = TSNE(n_components=2, init="random", random_state=42)
    return tsne.fit_transform(array)


def query_whisperer(prompt: str) -> str:
    """Synchronously call the Whisperer service."""

    return asyncio.run(call_whisperer(prompt))


def main() -> None:
    st.title("\u2728 Enriched Vector Cluster Explorer")

    df = load_enriched_vectors()

    method = st.selectbox("Dimensionality reduction", ["umap", "tsne"])
    coords = reduce_vectors(df["vector"], method)
    df["x"], df["y"] = coords[:, 0], coords[:, 1]

    fig = px.scatter(df, x="x", y="y", hover_name="id", title="Vector Clusters")
    st.plotly_chart(fig, use_container_width=True)

    selected_id = st.selectbox("Vector ID", df["id"])
    question = st.text_input("Ask Whisperer about this vector")
    if st.button("Query") and question:
        prompt = f"Vector {selected_id}: {question}"
        with st.spinner("Querying Whisperer..."):
            response = query_whisperer(prompt)
        st.markdown(f"**Whisperer:** {response}")


if __name__ == "__main__":  # pragma: no cover - streamlit entry point
    main()
