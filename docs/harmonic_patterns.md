# Harmonic Pattern Detection

The enrichment pipeline can surface classic harmonic price patterns using
`core.harmonic_processor.HarmonicProcessor`.  Patterns are detected from
OHLC bars and can be merged with `AdvancedProcessor` outputs for a
unified payload.

## Supported patterns

The detector recognises the following Fibonacci-based structures:

- **Gartley**
- **Butterfly**
- **Bat**
- **Crab**
- **Shark**
- **Cypher**
- **Three Drives**
- **ABCD**

## Return schema

`HarmonicProcessor.analyze` returns a dictionary containing
`harmonic_patterns`, where each pattern entry has:

```json
{
  "pattern": "GARTLEY",
  "points": [{"index": 10, "price": 1.2345}, ...],
  "prz": {"min": 1.2300, "max": 1.2400},
  "confidence": 0.8
}
```

`points` lists the five pivot locations forming the pattern. `prz`
shows the potential reversal zone bounds, and `confidence` is a simple
heuristic based on the number of recognised points.

## Tolerance settings

Fibonacci ratios are validated with a default tolerance of **5%**
(`tolerance=0.05` in `_validate_pattern_structure`).  Adjust the value
when initialising a custom detector if stricter or looser matching is
required.

## Performance notes

Pattern detection is a lightweight loop over local pivots. On synthetic
data of 1,000 rows the analysis completed in roughly **3.35 ms**,
scaling linearly with input size.

## Example: merging with `AdvancedProcessor`

```python
import pandas as pd
from utils.processors import AdvancedProcessor
from core.harmonic_processor import HarmonicProcessor

# Minimal OHLC sample; use real market data in practice
bars = pd.DataFrame({
    "open":  [1,2,3,4,5,4,3,2,3,4],
    "high":  [1,2,3,4,5,4,3,2,3,4],
    "low":   [1,2,3,4,5,4,3,2,3,4],
    "close": [1,2,3,4,5,4,3,2,3,4],
})

proc = AdvancedProcessor()
analysis = proc.process(bars)
analysis.update(HarmonicProcessor().analyze(bars))
print(analysis["harmonic_patterns"])  # list of detected patterns
```

The combined `analysis` dictionary now includes harmonic pattern
information alongside fractals, pivots, and other metrics produced by
`AdvancedProcessor.process`.
