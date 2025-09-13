import importlib
import sys
import types
import numpy as np


class FakeIndexFlatL2:
    def __init__(self, dimension: int):
        self.dimension = dimension
        self.vectors: list[np.ndarray] = []

    def add(self, vec_array: np.ndarray) -> None:
        for vec in vec_array:
            self.vectors.append(vec)

    def search(self, vec: np.ndarray, top_k: int):
        if not self.vectors:
            return np.array([[]], dtype="float32"), np.array([[]], dtype="int64")
        arr = np.stack(self.vectors)
        dists = np.sum((arr - vec) ** 2, axis=1)
        idxs = np.argsort(dists)[:top_k]
        return np.array([dists[idxs]], dtype="float32"), np.array([idxs], dtype="int64")

    @property
    def ntotal(self) -> int:
        return len(self.vectors)


faiss_stub = types.ModuleType("faiss")
faiss_stub.IndexFlatL2 = FakeIndexFlatL2
sys.modules.setdefault("faiss", faiss_stub)


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


def test_faiss_storage(monkeypatch):
    cfg = _reload_module(monkeypatch, {"VECTOR_DIMENSION": "3"})
    cfg.add_vectors([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]], [101, "b"])
    res = cfg.query_vector([1.0, 0.0, 0.0], top_k=1)
    assert res and res[0]["id"] == 101
