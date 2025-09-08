# Whisperer × Zanzibar × Zanflow v17 — Boot Orchestrator

This pack fuses the behavioral layer (The Whisperer), your constitutional rules (Zanzibar), and Zanflow v17’s structural trading flows into a single bootable configuration for LLM sessions.

Contents
- `whisperer_zanflow_master.yaml` — Master boot config (identity, rules, KBs, actions, flows)
- Referenced KBs (expected alongside):
  - `docs/gpt_llm/whisperer_prompts.yaml`, `mental_support.yaml`, `prompt_library.yaml`, `natural_language_dsl.yaml`, `suggestions.yaml`, `prompts.yaml`, `personal_assistant.yaml`
  - `docs/gpt_llm/ZANZIBAR_AGENT_INSTRUCTIONS.md`
  - `docs/gpt_llm/zanflow_logical_blocks.yaml`, `zanflow_prompt_engineering_system.json`, `zanflow_structural_flow.json`, `zanflow_v17_menu_system.json`, `zanflow_v17_quick_reference.txt`

Usage (Boot Orchestrator)
1) Load the master YAML
- Read and parse `whisperer_zanflow_master.yaml`
- Set the LLM system prompt from `system_identity` (name, role, style, hard_rules)

2) Mount knowledge bases (KBs)
- For each path in `knowledge_bases`, load if present and attach to the LLM context
- Missing files do not break boot; log and continue

3) Register actions and flows
- Expose `actions_available` to the UI/menu
- Configure `action_bindings` → calls map to existing API endpoints (prefer Actions Bus)
- Load `prompt_flows` as named sequences (behavioral_recovery, market_analysis, trade_execution)

4) Seed context
- Call `GET /api/v1/state/snapshot` to hydrate mirror/patterns/risk/equity
- Optionally pull `GET /api/v1/market/mini` after seeding (requires `/api/v1/market/fetch` in cron)

5) Confirm ready
- Output `startup_confirmation.message` once boot is complete

Live API references (no mock data)
- Actions Bus (slim): `POST /api/v1/actions/query` → verbs `trades_recent`, `whisper_suggest`
- Candles: `GET /api/v1/feed/bars-enriched?symbol={SYM}&timeframe=M15&limit=200` (includes `bars`, `strategies`, `links`)
- Snapshot: `GET /api/v1/state/snapshot`
- Protect: `GET /api/v1/positions/{ticket}/protect`
- VIX/DXY: `GET /api/v1/market/fetch` → `GET /api/v1/market/mini`

Extending
- Add a strategy: define a new logical block (zanflow_logical_blocks.yaml), extend `zanflow_structural_flow.json`, and add a new flow in `prompt_flows`
- Add a behavioral trigger: extend `mental_support.yaml` and add a recovery flow
- Add Actions Bus verbs without growing main OpenAPI (update `openapi.actions.yaml`)

Operational Notes
- Price integrity: confirm with `/api/v1/feed/bars-enriched?limit=1` before quoting
- SoD sessions: trading day starts 23:00 Europe/London; `POST /api/v1/account/sod` can override per day
- Cooldowns: server‑side; avoid spamming whispers

This pack keeps the LLM specialized from the first token: identity + rules + menus + flows + KBs. It boots as a disciplined co‑pilot aligned to your Zanflow v17 execution logic.

