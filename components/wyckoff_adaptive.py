from __future__ import annotations
import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

PHASES = ["Accumulation", "Markup", "Distribution", "Markdown"]

@dataclass
class WyckoffPhaseOut:
    phase_logits: np.ndarray
    phase_labels: np.ndarray
    reasons: List[Dict]

@dataclass
class WyckoffEventOut:
    events_mask: Dict[str, np.ndarray]
    reasons: List[Dict]


def _nz(a, fill=0.0):
    return np.nan_to_num(a, nan=fill, posinf=fill, neginf=fill)


def _apply_news_buffer(
    logits: np.ndarray,
    feat: pd.DataFrame,
    news_times: Optional[List[pd.Timestamp]] = None,
    pre_bars: int = 2,
    post_bars: int = 2,
    volz_thresh: float = 3.0,
    clamp: float = 0.6,
) -> Tuple[np.ndarray, np.ndarray]:
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


def compute_adaptive_features(df: pd.DataFrame, win: int = 50) -> pd.DataFrame:
    out = df.copy()
    if "volume" not in out:
        out["volume"] = out.get("tick_volume", pd.Series(1.0, index=out.index))
    ret = out["close"].pct_change().fillna(0.0)
    out["ret"] = ret
    vol = out["volume"].astype(float)
    vol_z = (vol - vol.rolling(win).mean()) / (vol.rolling(win).std() + 1e-12)
    out["vol_z"] = vol_z.fillna(0.0)
    ma = out["close"].rolling(win).mean()
    sd = out["close"].rolling(win).std()
    upper = ma + 2 * sd
    lower = ma - 2 * sd
    pctB = (out["close"] - lower) / ((upper - lower) + 1e-12)
    out["bb_pctB"] = pctB.fillna(0.0)
    out["effort"] = out["vol_z"].values
    out["result"] = ret.abs().rolling(3).mean().fillna(0.0).values
    out["effort_result_ratio"] = _nz(out["effort"]) / (_nz(out["result"]) + 1e-6)
    return out


def identify_phases_adaptive(feat: pd.DataFrame) -> WyckoffPhaseOut:
    N = len(feat)
    logits = np.zeros((N, 4), dtype="float32")
    labels = np.array(["Neutral"] * N, dtype=object)
    reasons = [{} for _ in range(N)]
    vol_z = _nz(feat["vol_z"].values)
    bb = _nz(feat["bb_pctB"].values)
    eff_res = _nz(feat["effort_result_ratio"].values)
    drift = _nz(feat["ret"].rolling(5).mean().values)
    acc = (-vol_z) + (0.5 - np.abs(bb - 0.3)) + np.tanh(eff_res - 1.0)
    mup = (bb - 0.6) + np.clip(vol_z, -0.5, 1.0) * 0.2 + np.tanh(drift * 20)
    dst = (vol_z) + (0.5 - np.abs(bb - 0.8)) + np.tanh(eff_res - 1.0)
    mdk = (0.4 - bb) + np.clip(vol_z, -0.5, 1.0) * 0.2 + np.tanh(-drift * 20)
    raw = np.vstack([acc, mup, dst, mdk]).T.astype("float32")
    gate = np.clip(np.tanh(eff_res - 0.6) + 0.7, 0.3, 1.2).astype("float32")
    logits[:] = raw * gate[:, None]
    idx = np.argmax(logits, axis=1)
    conf = logits[np.arange(N), idx]
    chosen = np.array([PHASES[i] for i in idx])
    chosen[conf < 0.2] = "Neutral"
    labels[:] = chosen
    return WyckoffPhaseOut(logits, labels, reasons)


def detect_events_adaptive(feat: pd.DataFrame, lookback: int = 50) -> WyckoffEventOut:
    hi = feat["high"].rolling(lookback).max()
    lo = feat["low"].rolling(lookback).min()
    vol_z = _nz(feat["vol_z"].values)
    ret_fwd = _nz(feat["close"].pct_change().rolling(3).sum().shift(-3).values)
    spring = (
        (_nz(feat["low"].values) < _nz(lo.values) * 0.995)
        & (ret_fwd > 0.002)
        & (vol_z > 0.5)
    )
    upthrust = (
        (_nz(feat["high"].values) > _nz(hi.values) * 1.005)
        & (ret_fwd < -0.002)
        & (vol_z > 0.5)
    )
    return WyckoffEventOut(events_mask={"Spring": spring, "Upthrust": upthrust}, reasons=[])


def vsa_flags(feat: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame(index=feat.index)


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
    ph.phase_logits, news_mask = _apply_news_buffer(
        ph.phase_logits, feat, news_times=news_times, **news_cfg
    )
    ev = detect_events_adaptive(feat, lookback=win)
    return {
        "phases": {"logits": ph.phase_logits, "labels": ph.phase_labels, "reasons": ph.reasons[-200:]},
        "events": ev.events_mask,
        "vsa": vsa_flags(feat),
        "effort_result": feat[["effort", "result", "effort_result_ratio"]],
        "news_mask": news_mask,
    }
