from __future__ import annotations
import numpy as np
import pandas as pd
from typing import Dict


class WyckoffGuard:
    def __init__(self, vol_gate: float = 1.2, eff_gate: float = 0.8):
        self.vol_gate, self.eff_gate = vol_gate, eff_gate

    def suppress(self, labels: np.ndarray, vol_z: np.ndarray, eff_ratio: np.ndarray) -> Dict[str, np.ndarray]:
        is_dist = labels == "Distribution"
        is_acc = labels == "Accumulation"
        suppr_dist = is_dist & (vol_z < np.log1p(self.vol_gate)) & (eff_ratio < self.eff_gate)
        suppr_acc = is_acc & (vol_z < np.log1p(self.vol_gate)) & (eff_ratio < self.eff_gate)
        return {"suppress_distribution": suppr_dist, "suppress_accumulation": suppr_acc}


class SpringVerifier:
    def __init__(self, fwd_window: int = 10, vol_z_min: float = 0.5, fwd_ret_min: float = 0.002):
        self.w, self.vmin, self.rmin = fwd_window, vol_z_min, fwd_ret_min

    def confirm(self, df: pd.DataFrame, spring_mask: np.ndarray, upthrust_mask: np.ndarray) -> Dict[str, np.ndarray]:
        c = df["close"].values
        v = df.get("vol_z", pd.Series(0, index=df.index)).values
        ret_fwd = np.zeros_like(c)
        if len(c) > self.w:
            ret_fwd[:-self.w] = (c[self.w:] - c[:-self.w]) / np.maximum(c[:-self.w], 1e-9)
        return {
            "Spring_confirmed": spring_mask & (ret_fwd > self.rmin) & (v > self.vmin),
            "Upthrust_confirmed": upthrust_mask & (ret_fwd < -self.rmin) & (v > self.vmin),
        }


class MultiTFResolver:
    def resolve(self, l1m, l5m, l15m) -> Dict[str, np.ndarray]:
        n = min(len(l1m), len(l5m), len(l15m))
        l1, l5, l15 = l1m[-n:], l5m[-n:], l15m[-n:]
        bull = (l5 == "Markup") | (l15 == "Markup")
        bear = (l5 == "Markdown") | (l15 == "Markdown")
        conflict = ((l1 == "Distribution") & bull) | ((l1 == "Accumulation") & bear)
        return {"conflict_mask": conflict}
