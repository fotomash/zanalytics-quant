import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


def _nz(arr: np.ndarray) -> np.ndarray:
    arr = np.asarray(arr, dtype=float)
    arr[np.isnan(arr)] = 0.0
    return arr


@dataclass
class PhaseResult:
    phase_logits: np.ndarray
    phase_labels: np.ndarray
    reasons: List[str]


def compute_adaptive_features(df: pd.DataFrame, win: int = 50) -> pd.DataFrame:
    """Compute minimal feature set for adaptive Wyckoff analysis."""
    feat = pd.DataFrame(index=df.index)
    ret = df["close"].pct_change().abs().fillna(0)
    mean = ret.rolling(win, min_periods=1).mean()
    std = ret.rolling(win, min_periods=1).std().replace(0, np.nan)
    feat["vol_z"] = ((ret - mean) / std).fillna(0)
    close = df["close"].astype(float)
    bb_mid = close.rolling(win, min_periods=1).mean()
    bb_std = close.rolling(win, min_periods=1).std().fillna(0)
    feat["bb_pctB"] = ((close - (bb_mid - 2 * bb_std)) / (4 * bb_std)).fillna(0)
    return feat


def identify_phases_adaptive(feat: pd.DataFrame) -> PhaseResult:
    """Return crude logits/labels for phases based on pctB."""
    pct = feat["bb_pctB"].values
    logits = np.vstack([-pct, pct, -pct, pct]).T
    phases = np.array(["Accumulation", "Markup", "Distribution", "Markdown"])
    labels = phases[np.argmax(logits, axis=1)]
    reasons = ["auto"] * len(labels)
    return PhaseResult(phase_logits=logits, phase_labels=labels, reasons=reasons)


@dataclass
class EventResult:
    events_mask: Dict[str, np.ndarray]
    reasons: List[str]


def detect_events_adaptive(feat: pd.DataFrame, lookback: int = 50) -> EventResult:
    pct = feat["bb_pctB"].values
    spring = pct < 0.1
    up = pct > 0.9
    reasons = ["spring" if s else "upthrust" if u else "" for s, u in zip(spring, up)]
    return EventResult(events_mask={"Spring": spring, "Upthrust": up}, reasons=reasons)


def vsa_flags(feat: pd.DataFrame) -> Dict[str, np.ndarray]:
    return {"dummy": np.zeros(len(feat), dtype=bool)}


def effort_vs_result_table(feat: pd.DataFrame) -> Dict[str, float]:
    return {"dummy": float(np.nanmean(feat["vol_z"]))}


# --- NEWS BUFFER ------------------------------------------------------------
def _apply_news_buffer(
    logits: np.ndarray,
    feat: pd.DataFrame,
    news_times: Optional[List[pd.Timestamp]] = None,
    pre_bars: int = 2,
    post_bars: int = 2,
    volz_thresh: float = 3.0,
    clamp: float = 0.6,
) -> Tuple[np.ndarray, np.ndarray]:
    """Clamp logits around high-impact news times when vol_z is extreme."""
    if not news_times or len(feat) == 0:
        return logits, np.zeros(len(feat), dtype=bool)

    idx = feat.index
    mask = np.zeros(len(idx), dtype=bool)
    for t in pd.to_datetime(news_times):
        j = idx.get_indexer([t], method="nearest")
        if len(j) and j[0] >= 0:
            lo = max(0, j[0] - pre_bars)
            hi = min(len(idx), j[0] + post_bars + 1)
            mask[lo:hi] = True

    high_vol = _nz(feat["vol_z"].values) > volz_thresh
    mask &= high_vol
    logits_clamped = logits.copy()
    logits_clamped[mask] *= clamp
    return logits_clamped, mask


def analyze_wyckoff_adaptive(
    df: pd.DataFrame,
    win: int = 50,
    news_times: Optional[List[pd.Timestamp]] = None,
    news_cfg: Dict | None = None,
) -> Dict:
    feat = compute_adaptive_features(df, win=win)
    ph = identify_phases_adaptive(feat)
    if news_cfg is None:
        news_cfg = {}
    ph_logits, news_mask = _apply_news_buffer(
        ph.phase_logits,
        feat,
        news_times=news_times,
        pre_bars=news_cfg.get("pre_bars", 2),
        post_bars=news_cfg.get("post_bars", 2),
        volz_thresh=news_cfg.get("volz_thresh", 3.0),
        clamp=news_cfg.get("clamp", 0.6),
    )
    ph.phase_logits = ph_logits
    ev = detect_events_adaptive(feat, lookback=win)
    return {
        "phases": {
            "logits": ph.phase_logits,
            "labels": ph.phase_labels,
            "reasons": ph.reasons[-200:],
        },
        "events": {k: v for k, v in ev.events_mask.items()},
        "events_reasons": ev.reasons[-200:],
        "vsa": vsa_flags(feat),
        "effort_result": effort_vs_result_table(feat),
        "diagnostics": {
            "mean_vol_z": float(np.nanmean(feat["vol_z"])),
            "mean_bb_pctB": float(np.nanmean(feat["bb_pctB"])),
        },
        "news_mask": news_mask,
    }
