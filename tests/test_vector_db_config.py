import importlib
import sys
import types

import numpy as np


def _reload_module(monkeypatch, env):
    for key, value in env.items():
        if value is None:
            monkeypatch.delenv(key, raising=False)
        else:
            monkeypatch.setenv(key, value)
    if "analytics.vector_db_config" in sys.modules:
        del sys.modules["analytics.vector_db_config"]
    import analytics.vector_db_config as cfg
    return importlib.reload(cfg)


def test_local_faiss_storage(monkeypatch):
    cfg = _reload_module(
        monkeypatch,
        {"PINECONE_URL": "https://localhost:443", "VECTOR_DIMENSION": "3"},
    )
    cfg.add_vectors([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]], ["a", "b"])
    res = cfg.query_vector([1.0, 0.0, 0.0], top_k=1)
    assert res and res[0]["id"] == "a"


def test_remote_pinecone_storage(monkeypatch):
    class FakeIndex:
        def __init__(self):
            self.vectors = {}

        def upsert(self, vectors):
            for id_, vec, meta in vectors:
                self.vectors[id_] = (np.array(vec), meta)

        def query(self, vector, top_k, include_metadata=True):
            dists = []
            for id_, (vec, meta) in self.vectors.items():
                dist = float(np.linalg.norm(vec - np.array(vector)))
                dists.append((dist, id_, meta))
            dists.sort(key=lambda x: x[0])
            matches = [types.SimpleNamespace(id=i, score=-d, metadata=m) for d, i, m in dists[:top_k]]
            return types.SimpleNamespace(matches=matches)

    indexes: dict[str, FakeIndex] = {}

    def fake_pinecone_module():
        def init(api_key=None, environment=None):
            pass

        def list_indexes():
            return list(indexes.keys())

        def create_index(name, dimension):
            indexes[name] = FakeIndex()

        def Index(name):
            return indexes[name]

        return types.SimpleNamespace(
            init=init, list_indexes=list_indexes, create_index=create_index, Index=Index
        )

    monkeypatch.setitem(sys.modules, "pinecone", fake_pinecone_module())
    cfg = _reload_module(
        monkeypatch,
        {
            "PINECONE_URL": "https://example.com",
            "PINECONE_API_KEY": "key",
            "PINECONE_ENVIRONMENT": "env",
            "PINECONE_INDEX_NAME": "test-index",
            "VECTOR_DIMENSION": "3",
        },
    )
    cfg.add_vectors([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]], ["a", "b"])
    res = cfg.query_vector([0.0, 1.0, 0.0], top_k=1)
    assert res and res[0]["id"] == "b"
