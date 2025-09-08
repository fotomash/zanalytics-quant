Journaling Guide (ZBAR)
=======================

Purpose
- Persist structured records for entries, closes, partials, hedges, and SL/TP modifications.
- Enable audits, analytics, and behavioral scoring.

Schema
- JSON Schema lives at `docs/schemas/journal_entry.schema.json`.
- Required top-level fields: `timestamp`, `kind`, `trade_id`, `agent_id`, `text`.
- Recommended `meta` fields: ticket, symbol, side, volume_before, volume_action, volume_remaining, action_price, pnl_action, sl, tp, reason, session, htf_bias, confluence.

Kinds
- `ENTRY`, `CLOSE`, `PARTIAL_CLOSE`, `HEDGE`, `ORDER_MODIFY`.

Django helper
- `backend/django/app/nexus/journal_service.py`
  - `journal_append(kind, text, *, meta=None, trade_id=None, tags=None, agent_id=None, timestamp=None)`
  - `journal_append_structured(kind, trade_id, text, *, agent_id=None, tags=None, meta=None)` → stamps ISO-8601 UTC timestamp.

Where it is called
- `views_positions.py` appends entries for CLOSE/PARTIAL_CLOSE, HEDGE, ORDER_MODIFY with structured `meta`.

Example entry
```json
{
  "timestamp": "2025-09-08T19:45:12Z",
  "kind": "PARTIAL_CLOSE",
  "trade_id": 302402468,
  "agent_id": "zanflow_v17",
  "text": "Closed 50% of XAUUSD short",
  "tags": ["position_close", "risk_action", "partial"],
  "meta": {
    "ticket": 302402468,
    "symbol": "XAUUSD",
    "side": "SELL",
    "volume_before": 5.0,
    "volume_action": 2.5,
    "volume_remaining": 2.5,
    "entry_price": 3641.09,
    "action_price": 3636.2,
    "pnl_action": -1325.0,
    "sl": null,
    "tp": null,
    "reason": "manual_request",
    "session": "NY",
    "htf_bias": "bearish",
    "confluence": {
      "liquidity_sweep": false,
      "choch_bos": false,
      "wyckoff_phase": null
    }
  }
}
```

Notes
- Set `AGENT_ID` in environment to tag agent origin automatically (`journal_service` uses it as a default).
- Validation can be added before append (optional) using the schema.

