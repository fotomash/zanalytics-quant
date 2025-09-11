# Unified Analysis Payload V1

`UnifiedAnalysisPayloadV1` aggregates several analytic dimensions into a single
object for transport between services. The schema is implemented with
[pydantic](https://docs.pydantic.dev/) models in `schemas/payloads.py`.

## Top level fields

| Field | Type | Description |
|-------|------|-------------|
| `symbol` | `str` | Instrument identifier |
| `timeframe` | `str` | Timeframe for the analysis (e.g. `1m`, `1h`) |
| `timestamp` | `datetime` | When the analysis snapshot was taken |
| `market_context` | `MarketContext` | High level market information |
| `technical_indicators` | `TechnicalIndicators` | Common indicator values |
| `smc` | `SMCAnalysis` | Smart Money Concepts state |
| `wyckoff` | `WyckoffAnalysis` | Wyckoff phase and events |
| `microstructure` | `MicrostructureAnalysis` | Order flow and microstructure metrics |
| `extras` | `Dict[str, Any]` | Unstructured additional fields |

## Submodels

### MarketContext
- `symbol`: instrument identifier
- `timeframe`: timeframe for the context
- `session`: optional session label
- `trend`: optional textual trend description
- `volatility`: optional volatility measure

### TechnicalIndicators
- `rsi`, `macd`, `vwap`: common indicator values
- `moving_averages`: mapping of moving average names to values
- `extras`: additional indicator values keyed by name

### SMCAnalysis
- `market_structure`: textual market structure label
- `poi`: list of points of interest
- `liquidity_pools`: list of liquidity pool identifiers
- `notes`: optional free-form notes

### WyckoffAnalysis
- `phase`: current Wyckoff phase
- `events`: list of Wyckoff events
- `notes`: optional notes

### MicrostructureAnalysis
- `effective_spread`, `realized_spread`, `price_impact`: trade microstructure metrics
- `liquidity_score`, `toxicity_score`: derived scores

