# Yahoo Finance Chart Mapping Guide

This note documents how to reconstruct OHLCV bars from Yahoo Finance's chart API.

Endpoint
- `GET https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=...&range=...`

Arrays (aligned by index)
- `chart.result[0].timestamp[i]` (UNIX seconds)
- `chart.result[0].indicators.quote[0].open[i]`
- `...high[i]`, `...low[i]`, `...close[i]`, `...volume[i]`

Reconstruction
```
ts  = timestamp[i]
open = open[i], high = high[i], low = low[i], close = close[i], volume = volume[i]
```

Notes
- Some entries may be null; skip or forward-fill as needed.
- Convert `timestamp` to ISO UTC; intervals and ranges must be valid combinations supported by Yahoo.

Utilities
- `services/yf_client.py` provides a CLI to fetch + flatten bars:

```
python services/yf_client.py SPY --interval 1h --range 60d > spy_1h.json
```

