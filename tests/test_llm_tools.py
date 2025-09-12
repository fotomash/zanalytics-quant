import logging
from utils.llm_tools import extract_first_number


def test_extract_first_number_valid():
    assert extract_first_number("0.75") == 0.75


def test_extract_first_number_with_extra_text():
    assert extract_first_number("score: 0.5 (approx)") == 0.5


def test_extract_first_number_none(caplog):
    caplog.set_level(logging.WARNING)
    assert extract_first_number(None) == 0.0
    assert "extract_first_number received None" in caplog.text


def test_extract_first_number_invalid(caplog):
    caplog.set_level(logging.WARNING)
    assert extract_first_number("not a number") == 0.0
    assert "failed to parse" in caplog.text
