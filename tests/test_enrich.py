import uuid
from pathlib import Path

from utils.enrich import load_manifest, load_confidence_matrix
from utils import enrich_ticks

DATA_DIR = Path(__file__).parent / "enrich_samples"
MANIFEST_PATH = DATA_DIR / "manifest.json"
MATRIX_PATH = DATA_DIR / "matrix.json"


def test_load_manifest_and_matrix():
    manifest = load_manifest(MANIFEST_PATH)
    matrix = load_confidence_matrix(MATRIX_PATH)
    assert manifest["schema_version"] == "v1"
    assert "raw_calculation" in matrix


def test_trade_id_generation():
    enriched = enrich_ticks([{}], manifest_path=MANIFEST_PATH, matrix_path=MATRIX_PATH)[0]
    assert "trade_id" in enriched
    # ensure UUID hex format by attempting to parse
    uuid.UUID(enriched["trade_id"])


def test_embedding_vector_length():
    enriched = enrich_ticks([{}], manifest_path=MANIFEST_PATH, matrix_path=MATRIX_PATH)[0]
    assert len(enriched["embedding"]) == 384


def test_echonudge_phase_routing():
    ticks = [{"phase": "spring"}, {"phase": "markup"}]
    enriched = enrich_ticks(ticks, manifest_path=MANIFEST_PATH, matrix_path=MATRIX_PATH)
    assert "echonudge" in enriched[0]
    assert "echonudge" not in enriched[1]


def test_echonudge_threshold(monkeypatch):
    ticks = [{"phase": "markup"}]
    enriched = enrich_ticks(ticks, manifest_path=MANIFEST_PATH, matrix_path=MATRIX_PATH)
    assert "echonudge" not in enriched[0]
    monkeypatch.setattr("utils.enrich.LOCAL_THRESHOLD", 2.0)
    enriched = enrich_ticks(ticks, manifest_path=MANIFEST_PATH, matrix_path=MATRIX_PATH)
    assert "echonudge" in enriched[0]
