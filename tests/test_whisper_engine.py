import services.mcp2.llm_config as llm_config


def test_whisperer_handoff(monkeypatch):
    llm_config.call_whisperer = lambda prompt: "stub"
    from utils import correlation_intelligence_engine as cie

    monkeypatch.setattr(cie, "load_prompt", lambda key: "prompt")
    monkeypatch.setattr(
        cie,
        "call_local_echo",
        lambda p: '{"caution":"high","reason":"x","suggest":"y"}',
    )
    monkeypatch.setattr(cie, "call_whisperer", lambda p: '{"ae_pct":0.8}')

    ctx = {
        "symbol": "EURUSD",
        "phase": "bull",
        "corr_cluster": 0.1,
        "price": 1.0,
        "volume": 1.0,
        "rsi": 50,
        "sweep_prob": 0.1,
        "confidence": 0.6,
        "recent_loss_setups": 0,
    }
    out = cie.aware_caution_tick(ctx)
    assert out["ae_pct"] == 0.8
