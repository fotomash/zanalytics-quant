from services.behavioral_scorer.main import record_trade, RAPID_TRADE_THRESHOLD


def test_rapid_trades_reduce_patience():
    state = {"patience_score": 1.0}
    start = 1000.0
    for i in range(RAPID_TRADE_THRESHOLD + 1):
        record_trade(state, start + i)
    assert state["rapid_trade"] is True
    assert state["patience_score"] < 1.0
    prev = state["patience_score"]
    record_trade(state, start + RAPID_TRADE_THRESHOLD + 2)
    assert state["patience_score"] < prev
