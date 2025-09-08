Whisperer Guide
================

Purpose
- Provide succinct, context-aware coaching and nudges based on current confluence, risk envelope, and recent behavior.

Surfaces
- Actions Bus verb: `whisper_suggest`
  - Request: `{ "type": "whisper_suggest", "payload": { "symbol"?: string, "user_id"?: string } }`
  - Response: `{ message: string|null, heuristics: [...], meta: { user_id, symbol } }`
- SSE feed (optional): `GET /api/v1/feeds/stream?topics=whispers`
  - Streamed events with `event: whisper` and `data: {...}`

Server implementation
- Router: `backend/django/app/nexus/views.py` → `ActionsQueryView.post()` case `whisper_suggest`
- Engine: `whisper_engine.py` defines `WhisperEngine` and `State` input
  - Inputs include: confluence, patience index, trade frequency (trades_today), risk_budget_used_pct, etc.
  - Output: ranked heuristics with `message` field; top message returned in Actions response.

Dashboards
- Pulse Pro reads a quick `whispers_resp` (example in `dashboard/pages/21_pulse_pro.py`).
- SSE helpers in `dashboard/utils/streamlit_api.py` (`start_whisper_sse`, `drain_whisper_sse`) for live updates.

Acknowledgement / Actions (optional endpoints)
- `POST /api/pulse/whisper/ack` → acknowledge a whisper with reason
- `POST /api/pulse/whisper/act` → record follow-up action taken

Extending the Whisperer
- Add additional behavioral inputs to `WhisperEngine.State` as needed (e.g., fatigue index, streaks).
- Keep the `whisper_suggest` verb stable; only extend payload with optional fields.
- For high-frequency streaming, prefer the SSE channel to polling.

