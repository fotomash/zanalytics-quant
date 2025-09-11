Pulse Runtime (Active)
======================

Location: `backend/django/app/nexus/pulse/`

Modules
-------

- `gates.py` — gate evaluators
  - `structure_gate(m1)` — CHoCH/BoS + volume check
  - `liquidity_gate(m15)` — Asian/swing sweep + snap‑back
  - `risk_gate(imbalance, structure, symbol)` — stop at swing ± 3 pips; 1R/2R/3R targets
- `service.py` — data loader + `pulse_status(symbol)`
  - DB‑first via `Bar`; fallback to MT5 bridge; normalized OHLCV
  - Per‑TF lookbacks: H4=300, H1=600, M15=800, M1=1200
- `views.py` & `urls.py`
  - `/api/v1/feed/pulse-status` — 0/1 flags
  - `/api/v1/feed/pulse-detail` — structure/liquidity/risk detail (memoized ~3s)
- `journal/` — feature‑flagged Kafka journal (see docs/journal_envelopes.md)

Status
------

- Active and production direction
- Journal defaults disabled; enable via `USE_KAFKA_JOURNAL=true` in staging first

