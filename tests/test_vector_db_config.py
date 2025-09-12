import importlib
import sys


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
    cfg.add_vectors([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]], ["a", "b"])
    res = cfg.query_vector([1.0, 0.0, 0.0], top_k=1)
    assert res and res[0]["id"] == "a"
