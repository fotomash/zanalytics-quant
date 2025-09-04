import numpy as np
from typing import Dict

class MultiTFResolver:
    """Resolve multi-timeframe phase conflicts.

    The resolver checks for disagreement between labels from
    different timeframes and returns a boolean mask indicating where
    conflicts occur.
    """

    def resolve(self, labels_1m: np.ndarray, labels_5m: np.ndarray, labels_15m: np.ndarray) -> Dict[str, np.ndarray]:
        min_len = min(len(labels_1m), len(labels_5m), len(labels_15m))
        l1 = labels_1m[-min_len:]
        l5 = labels_5m[-min_len:]
        l15 = labels_15m[-min_len:]
        conflict = (l1 != l5) | (l1 != l15) | (l5 != l15)
        return {"conflict_mask": conflict}
