from __future__ import annotations
import numpy as np
import pandas as pd
from typing import Dict
from components.wyckoff_adaptive import analyze_wyckoff_adaptive, PHASES
from components.wyckoff_agents import WyckoffGuard, SpringVerifier


def _softmax(x):
    e_x = np.exp(x - np.max(x, axis=1, keepdims=True))
    return e_x / e_x.sum(axis=1, keepdims=True)


class WyckoffScorer:
    def __init__(self, w_phase=0.55, w_events=0.20, w_vsa=0.25):
        self.w_phase, self.w_events, self.w_vsa = w_phase, w_events, w_vsa
        self.guard = WyckoffGuard()
        self.verifier = SpringVerifier()

    def score(self, df: pd.DataFrame, news_times=None, news_cfg=None) -> Dict:
        wy = analyze_wyckoff_adaptive(df, win=50, news_times=news_times, news_cfg=news_cfg)
        logits = wy["phases"]["logits"]
        probs = _softmax(logits)
        tilt = probs[:, PHASES.index("Markup")] - probs[:, PHASES.index("Markdown")]

        suppr = self.guard.suppress(
            wy["phases"]["labels"],
            df.get("vol_z", pd.Series(0, index=df.index)),
            wy["effort_result"]["effort_result_ratio"],
        )
        if suppr["suppress_distribution"].any():
            probs[:, PHASES.index("Distribution")] *= 0.7
        if suppr["suppress_accumulation"].any():
            probs[:, PHASES.index("Accumulation")] *= 0.7

        conf = self.verifier.confirm(df, wy["events"]["Spring"], wy["events"]["Upthrust"])
        spring_boost = conf["Spring_confirmed"].astype(float) * 0.15
        upthrust_drag = conf["Upthrust_confirmed"].astype(float) * 0.15

        score_vec = np.clip(
            self.w_phase * tilt + self.w_events * (spring_boost - upthrust_drag),
            -1,
            1,
        )
        score_0_100 = ((score_vec + 1) * 50).astype("float32")
        last_idx = len(score_0_100) - 1
        last_label = str(wy["phases"]["labels"][last_idx])

        explain_reasons = [f"phase={last_label}"]
        if conf["Spring_confirmed"][last_idx]:
            explain_reasons.append("Spring✓")

        return {
            "score": float(score_0_100[last_idx]),
            "reasons": explain_reasons,
            "probs": probs,
            "events": wy["events"],
            "explain": {"bb_pctB": 0.0, "vol_z": 0.0, "effort_result": 0.0},
            "last_label": last_label,
            "news_mask": wy.get("news_mask"),
        }
