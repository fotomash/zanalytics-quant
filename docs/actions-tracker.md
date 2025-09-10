# Actions Tracker
Last synced: 2025-09-10T13:20:19+00:00

| Source | Name | Endpoint | Method | Description |
| --- | --- | --- | --- | --- |
| OPENAI_ACTIONS | actions_read | /api/v1/actions/read | GET | Query a read-only action via alias endpoint |
| OPENAI_ACTIONS | actions_query | /api/v1/actions/query | GET | Query a read-only action |
| OPENAI_ACTIONS | actions_execute | /api/v1/actions/query | POST | Execute an action via the Actions Bus |
| OPENAI_ACTIONS | position_close | /api/v1/positions/close | POST | Close full or partial position |
| OPENAI_ACTIONS | position_modify | /api/v1/positions/modify | POST | Modify SL/TP for an existing position |
| OPENAI_ACTIONS | position_modify_by_ticket | /api/v1/positions/{ticket}/modify | POST | Modify SL/TP for an existing position by ticket path |
| OPENAI_ACTIONS | position_hedge | /api/v1/positions/hedge | POST | Open an opposite-side hedge order for a position |
| OPENAI_ACTIONS | trade_open | /trade/open | POST | Open a new trading position |
| OPENAI_ACTIONS | trade_close | /trade/close | POST | Close an existing trading position |
| OPENAI_ACTIONS | trade_modify | /trade/modify | POST | Modify stop-loss or take-profit for a position |
| mcp_server | /mcp | /mcp | GET |  |
| mcp_server | /exec/{full_path:path} | /exec/{full_path:path} | GET, POST, PUT, PATCH, DELETE |  |
