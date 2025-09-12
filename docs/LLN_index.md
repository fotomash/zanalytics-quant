# LLN Index Schema

The advanced processor enriches market bars with several technical labels.  
This document tracks the fields exposed for downstream consumption.

## Advanced Processor Output

| Field | Type | Description |
|-------|------|-------------|
| `fractals.up` | `List[int]` | Indices of upward Bill Williams fractals |
| `fractals.down` | `List[int]` | Indices of downward fractals |
| `alligator.state` | `List[str]` | Bill Williams Alligator classification per bar |
| `volatility.atr` | `List[float]` | Average True Range values |
| `pivots.peaks` | `List[int]` | Swing high indices detected via SciPy `find_peaks` |
| `pivots.troughs` | `List[int]` | Swing low indices detected via `find_peaks` |
| `elliott_wave.label` | `str` | Detected Elliott Wave pattern label |
| `elliott_wave.score` | `float` | Confidence score (0-1) combining fractal and Alligator validation |

The `pivots` and `elliott_wave` sections enable higher level pattern
recognition.  Confidence scores incorporate Fibonacci retracement
heuristics and agreement with fractal and Alligator signals.
