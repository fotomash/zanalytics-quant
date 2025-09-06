import os
import requests

API = os.environ.get("PULSE_API_BASE", "http://localhost:8000/api/pulse")


def get_score_peek():
    return requests.get(f"{API}/score/peek", timeout=5).json()


def get_risk_summary():
    return requests.get(f"{API}/risk/summary", timeout=5).json()


def get_top_signals(n=3):
    return requests.get(f"{API}/signals/top?n={n}", timeout=5).json()


def get_recent_journal(limit=10):
    return requests.get(f"{API}/journal/recent?limit={limit}", timeout=5).json()
