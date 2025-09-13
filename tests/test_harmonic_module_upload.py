import pandas as pd

from services.enrichment.modules import harmonic_processor as hp


def test_harmonic_run_uploads_vectors(monkeypatch):
    calls: dict = {}

    def fake_run_data_module(state, required_cols, engine_factory, method="analyze"):
        state["harmonic_patterns"] = [
            {"pattern": "TEST", "points": [], "prz": {"min": 1, "max": 2}, "confidence": 0.5}
        ]
        return state

    class DummyVectorStore:
        def __init__(self, client, collection_name=""):
            pass

        async def upsert(self, vectors, payloads, ids):
            calls["vectors"] = vectors
            calls["payloads"] = payloads
            calls["ids"] = ids

    monkeypatch.setattr(hp, "run_data_module", fake_run_data_module)
    monkeypatch.setattr(hp, "QdrantClient", lambda **kwargs: object())
    monkeypatch.setattr(hp, "HarmonicVectorStore", DummyVectorStore)
    monkeypatch.setattr(hp, "embed", lambda text: [0.1])

    state = {"dataframe": pd.DataFrame()}
    cfg = {"upload": True, "collection": "foo"}
    hp.run(state, cfg)

    assert calls["vectors"] == [[0.1]]
    assert calls["payloads"][0]["pattern"] == "TEST"
    assert calls["ids"] == [0]

