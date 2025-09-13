import services.mcp2.llm_config as llm_config


def test_replay_scoring(monkeypatch):
    llm_config.call_whisperer = lambda prompt: "stub"
    from scripts.backtest_slice import evaluate_rows

    def fake_caution(ctx):
        if ctx["price"] > 1:
            ctx.update({"caution": "high", "ae_pct": 0.9})
        else:
            ctx.update({"caution": "none"})
        return ctx

    monkeypatch.setattr("scripts.backtest_slice.aware_caution_tick", fake_caution)
    rows = [
        {"price": 0.5, "ts": "2020-01-01", "outcome_r": "1", "ae_pct": "0.1"},
        {"price": 1.5, "ts": "2020-01-02", "outcome_r": "-1", "ae_pct": "0.9"},
    ]
    report = evaluate_rows(rows, ae_thr=0.5, block_policy="med_high")
    assert report["count"] == 2
    assert report["escalation_rate"] == 0.5
    assert report["hit_rate_cautions"] == 1.0
