Positions, Partials, Scaling, Hedging
=====================================

Overview
- Friendly aliases (Django): `/api/v1/positions/{open,close,modify,hedge}`
- Core orders proxy: `/api/v1/orders/{market,modify,close}` (truth; talks to MT5 bridge)
- MT5 bridge (Flask): `/send_market_order`, `/partial_close_v2`, `/scale_position`, `/hedge`

Quick reference
- Open: POST `/api/v1/positions/open` (alias → `/api/v1/orders/market`)
  { symbol, side, volume, sl?, tp?, comment? }
  - Aliases accepted: `instrument`→symbol, `action`→side, `lots`/`qty`→volume
- Close full/partial: POST `/api/v1/positions/close`
  { ticket, fraction? | volume? }
  - Alias: `id`→ticket
- Modify SL/TP: POST `/api/v1/positions/modify` or `/api/v1/positions/<ticket>/modify`
  { ticket?, sl?, tp? }
  - Alias: `id`→ticket
- Hedge: POST `/api/v1/positions/hedge`
  { ticket, volume? }  (opposite side is inferred from the position)

LLM verbs (Actions Bus)
- `position_open`, `position_close`, `position_modify`, `position_hedge`
- All route through `POST /api/v1/actions/query`.

Volume safety
- The Django wrapper normalizes lots to a conservative step/min (default 0.01/0.01).
- The MT5 bridge also uses `symbol_info.volume_min/step` when available.

Partial close behavior
- Preferred input: `fraction` in (0,1). Optional absolute `volume` supported.
- Bridge endpoint `/partial_close_v2` can compute volume from fraction and ticket.

Scaling
- Bridge: `POST /scale_position { ticket, additional_volume }`

Hedging
- `POST /hedge { ticket, volume }` or `{ symbol, type: BUY|SELL, volume }`.
- On netting accounts, opposite orders net exposure; response includes a note.

Examples
- Close 25%
  curl -sX POST "$DJANGO/api/v1/positions/close" \
    -H 'Content-Type: application/json' \
    -d '{"ticket":302402468,"fraction":0.25}'

- Modify SL only
  curl -sX POST "$DJANGO/api/v1/positions/modify" \
    -H 'Content-Type: application/json' \
    -d '{"ticket":302402468,"sl":3625}'

- Modify TP via path
  curl -sX POST "$DJANGO/api/v1/positions/302402468/modify" \
    -H 'Content-Type: application/json' \
    -d '{"tp":3625}'

- Hedge full (uses current position volume)
  curl -sX POST "$DJANGO/api/v1/positions/hedge" \
    -H 'Content-Type: application/json' \
    -d '{"ticket":302402468}'

Diagnostics
- Streamlit page "24_Trades_Diagnostics" shows DB trades, MT5 history, and open positions.

