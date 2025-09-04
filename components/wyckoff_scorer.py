import numpy as np
import pandas as pd
from typing import Dict

from .wyckoff_adaptive import analyze_wyckoff_adaptive


class WyckoffScorer:
    """Lightweight scorer wrapping the adaptive Wyckoff analysis."""

    def __init__(self, w_phase: float = 0.33, w_events: float = 0.33, w_vsa: float = 0.34):
        self.w_phase = w_phase
        self.w_events = w_events
        self.w_vsa = w_vsa

    def score(self, df: pd.DataFrame) -> Dict:
        analysis = analyze_wyckoff_adaptive(df)
        logits = analysis["phases"]["logits"]
        # Softmax to probabilities
        exp_logits = np.exp(logits - logits.max(axis=1, keepdims=True))
        probs = exp_logits / exp_logits.sum(axis=1, keepdims=True)
        phase_score = float(np.mean(logits))
        event_score = float(sum(np.any(v) for v in analysis["events"].values()))
        vsa_score = float(np.mean(list(analysis["vsa"].get("dummy", [])))) if analysis["vsa"] else 0.0
        total = phase_score * self.w_phase + event_score * self.w_events + vsa_score * self.w_vsa
        return {
            "wyckoff_score": float(total),
            "wyckoff_probs": probs,
            "events": analysis["events"],
            "explain": analysis["events_reasons"],
            "news_mask": analysis.get("news_mask"),
        }
