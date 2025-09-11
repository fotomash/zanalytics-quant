# Actions Tracker

This file is the single source of truth for action status and links.

Last synced: 2025-09-10T13:20:19+00:00

## Status Legend

- **Stable**: Ready for general use
- **Draft**: Under active development
- **Planned**: Accepted but not yet implemented
- **Retired**: Removed from active use

Tracks active and planned actions with their schema references and documentation.

| Action | Schema Path | Authoritative Doc | Status | Core Function | Why | Future | Retired |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `/session/boot` | `openapi.actions.yaml#/components/schemas/SessionBootRequest` | [ACTIONS_BUS.md](ACTIONS_BUS.md) | Draft | Initialize agent session | Provide handshake and capabilities | Define schema and auth flow | No |
| `/exec/{cmd}` | N/A | [endpoints.md](endpoints.md) | Stable | Proxy requests to internal API | Expose single entry point for agent commands | Add auth and logging | No |
| `/tool/search` | `openapi.actions.yaml#/paths/~1tool~1search` | [ACTIONS_API_OVERVIEW.md](ACTIONS_API_OVERVIEW.md) | Planned | Search available tools | Allow agents to discover functionality | Schema under development | No |
| `/tool/fetch` | `openapi.actions.yaml#/paths/~1tool~1fetch` | [ACTIONS_API_OVERVIEW.md](ACTIONS_API_OVERVIEW.md) | Planned | Retrieve data using a specific tool | Fetch resources for analysis | Schema under development | No |
| `/mcp` | N/A | [endpoints.md](endpoints.md) | Stable | Stream MCP events | Provide real-time NDJSON heartbeat | Stream more event types | No |
| `/api/v1/positions/modify` | `openapi.yaml#/paths/~1api~1v1~1positions~1modify` | [POSITIONS_AND_ORDERS.md](POSITIONS_AND_ORDERS.md) | Stable | Modify SL/TP for an existing position | Adjust risk on open trades | Expand to volume modifications | No |
| `/api/v1/risk/query` | `openapi.yaml#/paths/~1api~1v1~1risk~1query` | [VERBS_CATALOG.md](VERBS_CATALOG.md) | Planned | Query risk metrics | Assess risk exposure | Schema pending | No |
