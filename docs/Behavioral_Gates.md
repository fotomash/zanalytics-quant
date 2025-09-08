# Behavioral & Misbehavioral Gates

This spec defines the behavioral gates (Discipline, Patience, Conviction, Efficiency) and how they influence UI and trading flow.

## Gate Model

- Score range: 0–100
- Bands: Low (<50, red), Mid (50–70, amber), High (>70, green)
- Thresholds are configurable per gate.

| Gate        | Inputs (examples)                                             | Effect if < threshold                              |
|-------------|----------------------------------------------------------------|-----------------------------------------------------|
| Discipline  | Journal events, revenge-trade flags, overtrading bursts        | Warn; reject risky actions; show rejection donut    |
| Patience    | Time-in-trade, time-between-trades, FOMO indicators            | Block early entries; start cooldown timer           |
| Conviction  | Setup quality, recent win-rate in conditions, signal strength  | Reduce position size; show caution icon             |
| Efficiency  | PnL vs exposure, captured vs potential                         | Alert on wasted risk; advise size reduction         |

## Gate Logic (pseudocode)

```python
from typing import Dict

BANDS = dict(high=70, mid=50)

def gate_band(score: float) -> str:
    s = float(score or 0)
    if s >= BANDS['high']: return 'green'
    if s >= BANDS['mid']:  return 'amber'
    return 'red'

def gate_effect(metric: str, score: float, threshold: float) -> Dict:
    band = gate_band(score)
    action = None
    if score < threshold:
        if metric == 'discipline':
            action = 'reject_risky_actions'
        elif metric == 'patience':
            action = 'cooldown_timer'
        elif metric == 'conviction':
            action = 'limit_size'
        elif metric == 'efficiency':
            action = 'warn_wasted_risk'
    return dict(metric=metric, score=score, band=band, action=action)
```

## Donut Gate Score (UI contract)

Use a small donut per gate, color-coded by band, with:
- Title (Gate name)
- Score (e.g., “56%”)
- Threshold marker (tick at threshold angle)
- Optional subtitle (“Recent misbehavior: revenge trade”)

```python
# conceptual API used by Streamlit/Plotly components

def donut_gate_score(title: str, score: float, threshold: float,
                      subtitle: str | None = None,
                      colors = { 'high': '#22C55E', 'mid': '#FBBF24', 'low': '#EF4444' }):
    """Render a single-ring donut with score arc and a threshold tick.
    - Map score (0..100) to 0..1 arc length.
    - Color by band from gate_band(score).
    - Add a thin tick at threshold/100 * 360°.
    """
    ...  # see compatible examples in docs/Donut_Confluence_Spec.md
```

## Integration Points

- Dashboard donuts already exist in `dashboard/components/ui_concentric.py` and `dashboard/utils/plotly_donuts.py`.
- Extend those helpers to add a single-ring gate donut with a threshold tick and label.
- Wire to mirror state (API: `GET /api/v1/mirror/state`) using keys: `discipline`, `patience`, `conviction`, `efficiency`.

