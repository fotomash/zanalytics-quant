# Whisperer Pack – Quick Install

Use this checklist to upload and enable the Whisperer pack for GPT.

1) Upload Knowledge files
- Upload these two YAMLs so GPT can read them directly:
  - docs/gpt_llm/whisperer_gpt_instructions.yaml
  - docs/gpt_llm/whisperer_zanflow_pack/whisperer_zanflow_master.yaml
- Optionally also upload the whole pack zip: whisperer_zanflow_pack.zip (GPT won’t unzip, but it’s useful for your orchestrator).

2) Configure Actions (OpenAPI)
- Add an Action with manifest: openapi.actions.yaml
- Server base URL: your Django host (e.g., https://mcp2.zanalytics.app)
- Endpoints exposed via Actions Bus:
  - POST /api/v1/actions/query with verbs: session_boot, trades_recent, trades_history_mt5, whisper_suggest

3) First run – opening action
- The instructions file triggers a default opening call:
  - { type: "session_boot", payload: { limit_trades: 10, include_positions: true, include_equity: true, include_risk: true } }
- Result is the initial awareness snapshot (trades, positions, equity, risk).

4) Closed trades view
- Hybrid flow tries DB first (trades_recent), then falls back to live MT5 (trades_history_mt5) if DB is empty.
- To persist history long‑term, add an MT5→DB sync job later.

5) Optional: cache + scheduler
- Server‑side cache: set SESSION_BOOT_TTL (seconds) to enable short‑term caching for session_boot.
- Client cache helpers: utils/session_cache.py (explicit + unified helpers).
- Session close scheduler: utils/session_scheduler.py with times in docs/gpt_llm/session_times.yaml

Quick sanity check
- Call POST /api/v1/actions/query → { "type": "session_boot" } — returns snapshot JSON
- Call POST /api/v1/actions/query → { "type": "trades_history_mt5", "payload": { "symbol": "XAUUSD", "date_from": "YYYY-MM-DD" } }

That’s it — the Whisperer boots aware, with actions wired, and a clear path to persistent history.

