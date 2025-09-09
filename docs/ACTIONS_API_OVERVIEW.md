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


