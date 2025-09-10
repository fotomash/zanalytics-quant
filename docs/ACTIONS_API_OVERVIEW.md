Zan.Pulse Actions API
=====================

The Actions API is the command layer for the Zan.Pulse system — a unified, schema-driven interface that handles all critical interactions between analysis, execution, journaling, and behavioral logic.

It works like a verb bus — you send a JSON object like this:

```json
{
  "type": "position_close",
  "payload": {
    "ticket": 302402468,
    "fraction": 0.5
  }
}
```

…and the system knows exactly what to do with it.


All valid actions are described in [`openapi.yaml`](../openapi.yaml), the
canonical schema for the verb bus. If a verb isn’t in that spec, it doesn’t
exist.

Why does it exist?
------------------
Zan.Pulse is built for precision, confluence, and human-AI parity. That means:

- All logic must be auditable.
- All decisions must be explainable.
- The interface must work for humans, dashboards, and agents alike.

The Actions API lets trading agents, dashboards, and monitoring tools speak the same language—structured, type-safe, and version-controlled.

What does it do?
----------------
It provides a consistent interface to do things like:

| Action | Example use case |
| ------ | ---------------- |
| `position_open` | Open a long trade on XAUUSD at volume 0.1 |
| `position_close` | Close half of an open trade |
| `pulse_status` | Get the current score and state of confluence |
| `journal_append` | Record that a trade was modified by user input |
| `behavior_events` | Log an overtrading warning |
| `whisper_suggest` | Ask the system to generate suggestions |

All of these use the same request format:

```json
{
  "type": "some_action_type",
  "payload": {
    // parameters specific to that action
  }
}
```

What does this approach achieve?
--------------------------------

### ✅ Consistency
All actions follow the same `type + payload` pattern, making the system easy to learn, use, and debug.

### ✅ Schema Validation
Every action is typed, validated, and contract-checked before execution—no loose inputs.

### ✅ Extensibility
To add a new verb like `equity_projection`:

1. Define a new schema.
2. Add a handler.
3. Register the type.

### ✅ Auditability
Every action can be logged, replayed (e.g., in backtests), and explained.

### ✅ AI/LLM Ready
Agents construct structured instructions using existing examples and schemas. No guesswork required.

Where does it fit?
------------------
This sits at the edge of the system:

- Above the MT5 execution logic
- Above the analyzers (SMC, Wyckoff, Technical)
- Integrated with RiskEnforcer, Whisperer, and Journal
- Exposed via `/api/v1/actions/query` for dashboards and services
- Plugged into Kafka streams and logs for real-time tracking

Think of it like this…
---------------------
Instead of building a UI that says:

> Call `POST /trades/close/` with these fields.

You're building a UI (or AI) that says:

> Tell the system what you want to do. Use a clear verb. Pass valid inputs. The system will do the rest.


Canonical integration plan
--------------------------
To keep the interface consistent and auditable, development around the Actions
API follows a strict plan:

1. **`type` drives the handler** – map the string to a central registry (e.g.
   `"position_close" → handle_position_close()`), never to hard‑coded logic.
2. **Validate `payload` against the schema** – enforce required fields and block
   unknown keys with Pydantic or an equivalent validator bound to
   `openapi.yaml`.
3. **Add schema before code** – every new action first lands in
   `openapi.yaml` with an example. Only after that do we implement the handler.
4. **Log everything** – persist `{type, payload, user, timestamp}` and return a
   result object noting success or failure.
5. **No schema drift** – when UI or agent behaviour changes, update the schema
   first, then handlers, then prompts or front‑end code.

Bonus: schema‑aware UIs (Streamlit, Whisperer, etc.) can render available verbs
directly from `openapi.yaml`.

Example flow:

```json
{
  "type": "journal_append",
  "payload": {
    "trade_id": 302402468,
    "kind": "CLOSE",
    "text": "Closed due to confluence drop"
  }
}
```

The backend validates this against `JournalAppendPayload`, logs it, streams it
to Kafka, and returns `{ "success": true }`.

MCP1 Integration
-----------------
The Actions schema also exposes `/api/v1/mcp1/authenticate` for realtime OpenAI services.
Send `{ "token": "<jwt>" }` and receive `{ "status": "authenticated" }` when valid.

See also:
- [Actions Bus](ACTIONS_BUS.md)
- [Verbs Catalog](VERBS_CATALOG.md)




