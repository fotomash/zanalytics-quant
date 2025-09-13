import sys
import types
import uuid
from pathlib import Path

import pytest


class _StubModel:
    class _Emb(list):
        def tolist(self):
            return list(self)

    def encode(self, text):
        return self._Emb([0.0] * 384)


sys.modules.setdefault(
    "sentence_transformers", types.SimpleNamespace(SentenceTransformer=lambda *a, **k: _StubModel())
)

import utils.enrich as enrich_mod
from utils import enrich_ticks

DATA_DIR = Path(__file__).parent / "enrich_samples"
MANIFEST_PATH = DATA_DIR / "manifest.json"
MATRIX_PATH = DATA_DIR / "matrix.json"


def test_load_manifest_and_matrix():
    manifest = enrich_mod.load_manifest(MANIFEST_PATH)
    matrix = enrich_mod.load_confidence_matrix(MATRIX_PATH)
    assert manifest["schema_version"] == "v1"
    assert "raw_calculation" in matrix


def test_trade_id_generation():
    enriched = enrich_ticks([{}], manifest_path=MANIFEST_PATH, matrix_path=MATRIX_PATH)[0]
    assert "trade_id" in enriched
    # ensure UUID hex format by attempting to parse
    uuid.UUID(enriched["trade_id"])


def test_embedding_vector_shape(monkeypatch):
    store: dict[str, list[float]] = {}

    def fake_store(embedding):
        pid = uuid.uuid4().hex
        store[pid] = embedding
        return pid

    monkeypatch.setattr("utils.enrich._store_embedding", fake_store)
    monkeypatch.setattr("utils.enrich.get_embedding", lambda pid: store.get(pid))

    enriched = enrich_ticks([{}], manifest_path=MANIFEST_PATH, matrix_path=MATRIX_PATH)[0]
    pid = enriched["embedding_id"]
    embedding = enrich_mod.get_embedding(pid)
    assert isinstance(embedding, list)
    assert embedding, "embedding should not be empty"


def test_embedding_fallback(monkeypatch):
    """When the model cannot be loaded a zero vector is returned."""

    # Force _get_model to attempt import which will fail via patched __import__
    monkeypatch.setattr("utils.enrich._MODEL", None)

    import builtins

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "sentence_transformers":
            raise ImportError
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    store: dict[str, list[float]] = {}

    def fake_store(embedding):
        pid = "id"
        store[pid] = embedding
        return pid

    monkeypatch.setattr("utils.enrich._store_embedding", fake_store)
    monkeypatch.setattr("utils.enrich.get_embedding", lambda pid: store.get(pid))

    enriched = enrich_ticks([{}], manifest_path=MANIFEST_PATH, matrix_path=MATRIX_PATH)[0]
    assert enriched["embedding_id"] == "id"
    assert store["id"] == [0.0] * 384


def test_echonudge_phase_routing():
    ticks = [{"phase": "spring"}, {"phase": "markup"}]
    enriched = enrich_ticks(ticks, manifest_path=MANIFEST_PATH, matrix_path=MATRIX_PATH)
    assert "echonudge" in enriched[0]
    assert "echonudge" not in enriched[1]


def test_echonudge_threshold(monkeypatch):
    ticks = [{"phase": "markup"}]
    enriched = enrich_ticks(ticks, manifest_path=MANIFEST_PATH, matrix_path=MATRIX_PATH)
    assert "echonudge" not in enriched[0]
    monkeypatch.setattr("services.mcp2.llm_config.LOCAL_THRESHOLD", 2.0)
    enriched = enrich_ticks(ticks, manifest_path=MANIFEST_PATH, matrix_path=MATRIX_PATH)
    assert "echonudge" in enriched[0]


@pytest.mark.parametrize("loader", [enrich_mod.load_manifest, enrich_mod.load_confidence_matrix])
def test_loader_missing_file(loader, tmp_path):
    missing = tmp_path / "missing.json"
    with pytest.raises(ValueError) as exc:
        loader(missing)
    assert "does not exist" in str(exc.value)


@pytest.mark.parametrize("loader", [enrich_mod.load_manifest, enrich_mod.load_confidence_matrix])
def test_loader_invalid_json(loader, tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("{invalid json", encoding="utf-8")
    with pytest.raises(ValueError) as exc:
        loader(bad)
    assert "Invalid JSON" in str(exc.value)
