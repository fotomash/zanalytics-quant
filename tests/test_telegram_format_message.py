from services.telegram import format_message


def test_format_message_basic():
    payload = {
        "symbol": "AAPL",
        "score": 0.95,
        "reasons": ["Reason 1", "Reason 2"],
        "warnings": ["Be cautious"],
    }
    msg = format_message(payload)
    assert "*Symbol*: AAPL" in msg
    assert "*Score*: 0.95" in msg
    assert "- Reason 1" in msg and "- Reason 2" in msg
    assert "_- Be cautious_" in msg


def test_format_message_missing_fields():
    msg = format_message({})
    assert "*Symbol*: Unknown" in msg
    assert "Score" not in msg
    assert "Reasons" not in msg
    assert "Warnings" not in msg


def test_format_message_length_limit():
    long_text = "a" * 5000
    msg = format_message({"symbol": "TEST", "reasons": [long_text]})
    assert len(msg) <= 4096
