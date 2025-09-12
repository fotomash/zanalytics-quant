Pulse SSE Test Client
---------------------

Quick static page to sanity check the Pulse SSE stream.

Usage
- Open `actions/sse_test.html` in a browser.
- Set `Base` to your Django host (e.g., `https://mcp2.zanalytics.app`).
- Select topics (whispers, market, mirror) and click Connect.
- Logs show raw SSE event payloads with timestamps.

URL Shortcuts
- You can deep-link with query params:
  - `?base=https://mcp2.zanalytics.app`
  - `&topics=mirror,whispers,market`

Notes
- SSE endpoint: `/api/v1/feeds/stream` emits `event: whisper|market|mirror` and a heartbeat.
- If you see CORS or network errors, ensure the host is reachable from your browser.

