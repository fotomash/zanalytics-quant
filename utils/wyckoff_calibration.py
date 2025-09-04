import numpy as np
import pandas as pd
from typing import Dict, List, Tuple

from components.wyckoff_scorer import WyckoffScorer


def _f1(tp: int, fp: int, fn: int) -> float:
    return tp / max(1e-9, (tp + 0.5 * (fp + fn)))


def _phase_f1(y_true: np.ndarray, y_pred: np.ndarray, phase: str) -> float:
    t = (y_true == phase)
    p = (y_pred == phase)
    tp = (t & p).sum()
    fp = (~t & p).sum()
    fn = (t & ~p).sum()
    return _f1(tp, fp, fn)


def evaluate_weights(
    df_list: List[pd.DataFrame],
    labels_list: List[np.ndarray],
    w_phase: float,
    w_events: float,
    w_vsa: float,
) -> Dict:
    scorer = WyckoffScorer(w_phase, w_events, w_vsa)
    f1_acc = []
    f1_dst = []
    spring_prec = []
    upthrust_prec = []
    for df, y_true in zip(df_list, labels_list):
        out = scorer.score(df)
        probs = out["wyckoff_probs"]
        phases = np.array(["Accumulation", "Markup", "Distribution", "Markdown"])
        y_pred = phases[np.argmax(probs, axis=1)]
        f1_acc.append(_phase_f1(y_true, y_pred, "Accumulation"))
        f1_dst.append(_phase_f1(y_true, y_pred, "Distribution"))
        if "label_spring" in df:
            pred_spring = out["events"].get("Spring", np.zeros(len(df), dtype=bool))
            tp = (df["label_spring"].values & pred_spring).sum()
            spring_prec.append(tp / max(1, pred_spring.sum()))
        if "label_upthrust" in df:
            pred_up = out["events"].get("Upthrust", np.zeros(len(df), dtype=bool))
            tp = (df["label_upthrust"].values & pred_up).sum()
            upthrust_prec.append(tp / max(1, pred_up.sum()))
    return {
        "f1_acc": float(np.mean(f1_acc)),
        "f1_dst": float(np.mean(f1_dst)),
        "spring_prec": float(np.mean(spring_prec) if spring_prec else np.nan),
        "upthrust_prec": float(np.mean(upthrust_prec) if upthrust_prec else np.nan),
    }


def grid_search_weights(
    df_list: List[pd.DataFrame],
    labels_list: List[np.ndarray],
) -> Tuple[float, float, float, Dict]:
    candidates = np.linspace(0.1, 0.7, 7)
    best = None
    best_metrics = None
    for w_phase in candidates:
        for w_events in candidates:
            w_vsa = max(0.0, 1.0 - (w_phase + w_events))
            if w_vsa < 0:
                continue
            m = evaluate_weights(df_list, labels_list, w_phase, w_events, w_vsa)
            score = (m["f1_acc"] + m["f1_dst"]) + 0.5 * np.nanmean(
                [m["spring_prec"], m["upthrust_prec"]]
            )
            if (best is None) or (score > best):
                best = score
                best_metrics = (w_phase, w_events, w_vsa, m)
    return (*best_metrics,)
