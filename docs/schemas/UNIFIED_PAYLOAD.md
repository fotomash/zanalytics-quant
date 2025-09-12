# Unified Analysis Payload V1

`UnifiedAnalysisPayloadV1` aggregates several analytic dimensions into a single
object for transport between services. The schema is implemented with
[pydantic](https://docs.pydantic.dev/) models in `schemas/payloads.py` and is
designed to be easily serialized to JSON. The enrichment service assembles this
payload after its pipeline completes and publishes the serialized JSON to the
`enriched-analysis-payloads` Kafka topic.

Typical creation pattern:

```python
from datetime import datetime
from schemas import (
    MarketContext,
    TechnicalIndicators,
    SMCAnalysis,
    WyckoffAnalysis,
    MicrostructureAnalysis,
    UnifiedAnalysisPayloadV1,
)

payload = UnifiedAnalysisPayloadV1(
    symbol="BTCUSD",
    timeframe="1m",
    timestamp=datetime.utcnow(),
    market_context=MarketContext(symbol="BTCUSD", timeframe="1m"),
    technical_indicators=TechnicalIndicators(rsi=55.2),
    smc=SMCAnalysis(),
    wyckoff=WyckoffAnalysis(),
    microstructure=MicrostructureAnalysis(),
)

# Serialize and publish
producer.produce(
    "enriched-analysis-payloads", payload.model_dump_json().encode("utf-8")
)
```

The resulting object can be `model_dump()`-ed to produce a standard JSON
payload for API communication.

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
| `extras` | `Dict[str, Any]` | Unstructured additional fields for forward compatibility |

## Submodels

### MarketContext

| Field | Type | Description |
|-------|------|-------------|
| `symbol` | `str` | Instrument identifier |
| `timeframe` | `str` | Timeframe for the context (e.g. `1m`, `1h`) |
| `session` | `Optional[str]` | Trading session label |
| `trend` | `Optional[str]` | Textual trend description (e.g. `bullish`) |
| `volatility` | `Optional[float]` | Volatility measure such as ATR |

### TechnicalIndicators

| Field | Type | Description |
|-------|------|-------------|
| `rsi` | `Optional[float]` | Relative Strength Index value |
| `macd` | `Optional[float]` | Moving Average Convergence Divergence value |
| `vwap` | `Optional[float]` | Volume Weighted Average Price |
| `moving_averages` | `Dict[str, float]` | Mapping of moving average names to values |
| `extras` | `Dict[str, Any]` | Additional indicator values keyed by name |

### SMCAnalysis

| Field | Type | Description |
|-------|------|-------------|
| `market_structure` | `Optional[str]` | Textual market structure label |
| `poi` | `List[str]` | Points of interest |
| `liquidity_pools` | `List[str]` | Identifiers of liquidity pools |
| `notes` | `Optional[str]` | Free-form notes |

### WyckoffAnalysis

| Field | Type | Description |
|-------|------|-------------|
| `phase` | `Optional[str]` | Current Wyckoff phase |
| `events` | `List[str]` | Wyckoff events observed |
| `notes` | `Optional[str]` | Additional notes |

### MicrostructureAnalysis

| Field | Type | Description |
|-------|------|-------------|
| `effective_spread` | `Optional[float]` | Effective spread metric |
| `realized_spread` | `Optional[float]` | Realized spread metric |
| `price_impact` | `Optional[float]` | Estimated price impact |
| `liquidity_score` | `Optional[float]` | Derived liquidity score |
| `toxicity_score` | `Optional[float]` | Derived toxicity score |

## Example JSON

Below is the JSON payload produced by `payload.model_dump()` using the example
creation snippet above:

```json
{
  "symbol": "BTCUSD",
  "timeframe": "1m",
  "timestamp": "2024-01-01T00:00:00Z",
  "market_context": {
    "symbol": "BTCUSD",
    "timeframe": "1m"
  },
  "technical_indicators": {
    "rsi": 55.2,
    "moving_averages": {},
    "extras": {}
  },
  "smc": {
    "poi": [],
    "liquidity_pools": []
  },
  "wyckoff": {
    "events": []
  },
  "microstructure": {},
  "extras": {}
}
```

## Usage Guidelines

- All timestamps should be UTC and ISO 8601 formatted when serialized.
- Optional fields may be omitted; consumers should handle their absence.
- Use the `extras` dictionaries for experimental or forward-compatible keys.
- When extending the schema, prefer adding to submodels rather than top-level
  fields to keep the payload organized.

