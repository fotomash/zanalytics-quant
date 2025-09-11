Dashboard Pages (Active)
========================

Highlights
----------

- Page 01 — Pulse – Intraday Trader View: real-time session/trade metrics with behavioral overlays; position manager with close/partial actions
- Page 12 — PULSE Flow: lights + Structure/Liquidity/Risk details; symbol picker with favorite setting
- Page 07 — ZANFLOW v12: Live/DB/Parquet fallbacks; symbol picker uses favorite
- Pages 16/17/19/20 — Risk dashboards; Settings sidebar includes favorite symbol; consistent styling

Shared preferences
------------------

- Favorite symbol persisted via `/api/v1/user/prefs`; helpers in `dashboard/utils/user_prefs.py`

Status badges
-------------

- Most dashboards are Active; some panels may say Experimental while Kafka parity is in progress.

