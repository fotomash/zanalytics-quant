# Whisperer Loader Notes

- `whisperer_zanflow_master.yaml` lists KBs by filename only (portable for flat uploads).
- The loader (`utils/loader_utils.py`) automatically resolves KB paths relative to the master YAML location:
  - Same directory as the master file
  - `behavioral/`, `strategy/`, `support/`, `constitutional/` subfolders

This means you can run either layout without changing the YAML:

- Flat upload (all files next to the master YAML)
- Full extracted pack at `docs/gpt_llm/whisperer_zanflow_pack/`

Example usage in your orchestrator:

```python
from utils.loader_utils import load_master_config

master_cfg = load_master_config(
    "docs/gpt_llm/whisperer_zanflow_pack/whisperer_zanflow_master.yaml"
)
kb_files = master_cfg["knowledge_bases_resolved"]

for kb in kb_files:
    # Attach each KB into the GPT context
    print("Loaded KB:", kb)
```

Tip: Keep the GPT system prompt slim (see `docs/gpt_llm/whisperer_gpt_instructions.yaml`) and let the master config + ActionBus power the boot sequence (default `session_boot`).

### Session Snapshot Caching

- `session_boot` snapshots can be cached in Redis for ~30s to avoid redundant API calls and keep UI/LLM views consistent.
- Configure via env `SESSION_BOOT_TTL` (seconds). Default: 30.
- Cache key format: `session_boot:{user_id}`.
- Client helper: `utils/session_cache.py` exposes `fetch_session_boot(api_url, token, user_id)` that reads from Redis first, then calls `POST /api/v1/actions/query` with `{ type: "session_boot", ... }` and refreshes the cache.

Example orchestrator usage:

```python
from utils.session_cache import (
    fetch_session_boot,
    fetch_trades_recent,
    fetch_risk_status,
    fetch_cached,
)

API_URL = "http://localhost:8010"  # or https://django.yourdomain
TOKEN = None  # set if your API requires auth

snapshot = fetch_session_boot(API_URL, TOKEN, user_id="alice")
trades = fetch_trades_recent(API_URL, TOKEN, limit=20, user_id="alice")
risk = fetch_risk_status(API_URL, TOKEN, user_id="alice")

# Or use the unified helper
snapshot2 = fetch_cached(API_URL, TOKEN, "session_boot", user_id="alice")
print(snapshot.keys(), len(trades.get("trades", [])), bool(risk))
```

### Redis Caching for High-Frequency Calls

- Cached endpoints: `session_boot`, `trades_recent`, `risk_status`.
- TTLs (env-configurable):
  - `SESSION_BOOT_TTL` (default 30s)
  - `TRADES_RECENT_TTL` (default 15s)
  - `RISK_STATUS_TTL` (default 20s)
- Cache keys: `{api_type}:{user_id}`
- Utility: `utils/session_cache.py` (explicit helpers + `fetch_cached(...)`).

Server-side cache (backend)
- The backend endpoint `POST /api/v1/actions/query` supports server-side caching for `session_boot` when the env `SESSION_BOOT_TTL` (or `ACTIONS_SESSION_BOOT_TTL`) is set to a positive number.
- Key format: `session_boot:{user_id}` where `user_id` comes from the request payload (or `REMOTE_USER`, default `global`).
- This reduces load and keeps snapshots consistent across clients without any client changes.
