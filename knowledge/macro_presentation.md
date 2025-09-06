# Macro Integration for Trade Intelligence Systems

This document outlines a structured framework for integrating macroeconomic data into a live trading intelligence system. The aim is to contextualize intra-asset behavior with intermarket dynamics and present clean, structured outputs to reinforce market bias and execution discipline.

## Macro Regime Model

Each session begins with a regime snapshot compiled from authoritative sources:

- **DXY** (US Dollar Index): directional momentum
- **UST 10Y**: yield level and trend
- **VIX**: implied volatility regime
- **Gold, Crude, Commodities**: capital flow bias
- **Open Interest / COT**: institutional positioning

These components generate a live **macro conviction score** aligned with intraday structural mapping.

## Presentation Layer

All macro inputs are stored per session and aligned with:

- Time window (session start/end)
- Asset structure state (Wyckoff/SMC)
- Volatility state
- Confirmation criteria (volume signatures, LTF shifts)
- Execution feedback

Each input is precisely timestamped and mapped to setup evaluations and journal logs.

## Downstream Uses

- Trader-facing pre-session map
- ML training set for setup validation
- Journaling engine (ZBAR)
- Dashboard snapshot integration
