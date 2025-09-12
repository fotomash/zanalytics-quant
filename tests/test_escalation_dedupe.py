import time
import types
import sys
import importlib.util
from pathlib import Path

import fakeredis

# Stub heavy dependencies used during module import
sys.modules.setdefault(
    "services.mcp2.llm_config",
    types.SimpleNamespace(call_local_echo=lambda *_a, **_k: "", call_whisperer=lambda *_a, **_k: ""),
)
sys.modules.setdefault("session_manifest", types.SimpleNamespace(load_prompt=lambda *_a, **_k: ""))

spec = importlib.util.spec_from_file_location(
    "cie", Path(__file__).resolve().parent.parent / "utils" / "correlation_intelligence_engine.py"
)
cie = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cie)


def test_escalation_dedupe_survives_restart(monkeypatch):
    server = fakeredis.FakeServer()
    key = ("EURUSD", "phase", 0.1)

    r1 = fakeredis.FakeRedis(server=server, decode_responses=True)
    monkeypatch.setattr(cie, "_RCLI", r1)
    cie.mark_escalated(key, within_secs=1)
    assert cie.recently_escalated(key, within_secs=1)

    r2 = fakeredis.FakeRedis(server=server, decode_responses=True)
    monkeypatch.setattr(cie, "_RCLI", r2)
    assert cie.recently_escalated(key, within_secs=1)

    time.sleep(1.1)
    r3 = fakeredis.FakeRedis(server=server, decode_responses=True)
    monkeypatch.setattr(cie, "_RCLI", r3)
    assert not cie.recently_escalated(key, within_secs=1)
