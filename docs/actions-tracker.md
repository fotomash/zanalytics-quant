# Actions Tracker

Tracks active and planned actions with their schema references and documentation.

| Action | Schema Path | Authoritative Doc | Status | Core Function | Why | Future | Retired |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `/session/boot` | — | — | Draft | Initialize agent session | Provide handshake and capabilities | Define schema and auth flow | No |
| `/exec/{cmd}` | — | [endpoints.md](endpoints.md) | Stable | Proxy requests to internal API | Expose single entry point for agent commands | Add auth and logging | No |
| `/tool/search` | — | — | Planned | Search available tools | Allow agents to discover functionality | Schema under development | No |
| `/tool/fetch` | — | — | Planned | Retrieve data using a specific tool | Fetch resources for analysis | Schema under development | No |
| `/mcp` | — | [endpoints.md](endpoints.md) | Stable | Stream MCP events | Provide real-time NDJSON heartbeat | Stream more event types | No |
| `/api/v1/positions/modify` | `openapi.yaml#/paths/~1api~1v1~1positions~1modify` | [POSITIONS_AND_ORDERS.md](POSITIONS_AND_ORDERS.md) | Stable | Modify SL/TP for an existing position | Adjust risk on open trades | Expand to volume modifications | No |
| `/api/v1/risk/query` | — | — | Planned | Query risk metrics | Assess risk exposure | Schema pending | No |

