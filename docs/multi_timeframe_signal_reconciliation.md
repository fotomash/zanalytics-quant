# Multi-Timeframe Signal Reconciliation

Multi-timeframe reconciliation ensures that low timeframe trades respect the narrative set by higher timeframes. Signals (e.g., Wyckoff phase labels or numeric scores) from several resolutions are aligned and merged before a trade decision is made.

## Pipeline

1. **Align timeframes** – `TimeframeConverter` resamples and synchronises multiple bar sets so that all signals reference the same closing time.
2. **Resolve conflicts** – `MultiTFResolver` compares lower-timeframe signals against higher ones. Conflicts are flagged and can be used to suppress or penalise trades.
3. **Weight scores** – an alternative resolver combines numeric scores from different timeframes using configurable weights and applies a penalty when divergence is too high.

## Algorithmic Rules

### Timeframe alignment
`TimeframeConverter` slices all dataframes to a common end time and exposes a helper to gather a multi-timeframe view of the latest bar【F:utils/timeframe_converter.py†L80-L117】.

### Wyckoff label conflict detection
`MultiTFResolver` focuses on Wyckoff phase labels. It aligns 1 min, 5 min and 15 min arrays, then flags a conflict when the 1 min label contradicts the higher timeframe bias (e.g., 1 min shows *Distribution* while higher frames are in *Markup*)【F:components/wyckoff_agents.py†L35-L42】.

### Weighted score reconciliation
For numeric scores, the resolver in `utils/mtf_resolver` computes a weighted average based on timeframe importance. When score divergence exceeds 40 points, the final score is penalised and a conflict flag is returned【F:utils/mtf_resolver.py†L1-L31】.

## Configuration Knobs

| Component | Option | Description |
|-----------|--------|-------------|
| `TimeframeConverter` | `timeframe_minutes` | Mapping of timeframe codes to minute counts, controlling which resamples are produced. |
| `MultiTFResolver` (scores) | `tf_weights` | Relative weight for each timeframe when aggregating numeric scores. |
| `MultiTFResolver` (scores) | divergence threshold | If `max(score) - min(score) > 40`, mark conflict and apply 10% penalty. |
| `WyckoffGuard` | `vol_gate`, `eff_gate` | Optional filters that suppress low-volume or low-efficiency phase labels before reconciliation【F:components/wyckoff_agents.py†L7-L16】. |

## Sample Output

```python
from components.wyckoff_agents import MultiTFResolver
import numpy as np

resolver = MultiTFResolver()
labels_1m  = np.array(["Markup", "Markup", "Distribution", "Distribution"])
labels_5m  = np.array(["Markup", "Markup", "Markup", "Markup"])
labels_15m = np.array(["Markup", "Markup", "Markup", "Markup"])
resolver.resolve(labels_1m, labels_5m, labels_15m)
# {'conflict_mask': array([False, False, True, True])}
```

```python
from utils.mtf_resolver import MultiTFResolver
resolver = MultiTFResolver()
resolver.resolve_conflicts({'M1': 20, 'M5': 80, 'M15': 85})
# {'score': 58.0, 'conflict': True, 'reason': 'Timeframe divergence detected'}
```

## Related Modules & Tests

- `components/wyckoff_agents.py` – Wyckoff utilities including `MultiTFResolver`.
- `utils/timeframe_converter.py` – timeframe resampling and alignment.
- `utils/mtf_resolver.py` – weighted multi-timeframe score resolver.
- Tests: `tests/test_wyckoff_edges.py::test_edge_mtf_resolver_flags_conflict` and `tests/test_wyckoff_extras.py::test_mtf_resolver_clamps_conflicts`.

