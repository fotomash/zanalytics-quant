# Actions

`POST /api/v1/actions/query` accepts an optional `approve` flag to skip UI confirmations.

- Include `{ "type": "session_boot", "approve": true }` or `{ "type": "equity_today", "approve": true }` to bypass the approval prompt.
- When `approve` is omitted or `false`, these actions respond with `{ "message": "Requires approval", "action_id": "g-<timestamp>" }`.
- Other action types ignore the flag and still require manual approval.

Use this when integrating with Whisperer to fetch data directly without pop-ups.
