import os
import time

import fakeredis

import whisper_engine
from whisper_engine import Cooldowns, Whisper, WhisperEngine


def _mk_whisper() -> Whisper:
    return Whisper(
        id="w1",
        ts=time.time(),
        category="test",
        severity="info",
        message="hi",
        reasons=[],
        actions=[],
        ttl_seconds=60,
        cooldown_key="test",
        cooldown_seconds=1,
        channel=["dash"],
    )


def test_dedupe_survives_restart(monkeypatch):
    os.environ["WHISPER_DEDUPE_TTL"] = "1"
    monkeypatch.setattr(whisper_engine, "DEDUPE_TTL_SECONDS", 1)
    server = fakeredis.FakeServer()

    r1 = fakeredis.FakeRedis(server=server)
    monkeypatch.setattr(Cooldowns, "_redis", classmethod(lambda cls: r1))
    e1 = WhisperEngine({})
    assert e1._dedupe_and_arm_cooldowns([_mk_whisper()], "u")

    r2 = fakeredis.FakeRedis(server=server)
    monkeypatch.setattr(Cooldowns, "_redis", classmethod(lambda cls: r2))
    e2 = WhisperEngine({})
    assert e2._dedupe_and_arm_cooldowns([_mk_whisper()], "u") == []

    time.sleep(1.1)
    r3 = fakeredis.FakeRedis(server=server)
    monkeypatch.setattr(Cooldowns, "_redis", classmethod(lambda cls: r3))
    e3 = WhisperEngine({})
    assert e3._dedupe_and_arm_cooldowns([_mk_whisper()], "u")

