---

# 🧠 SLPlacementHybrid Logic Specification

## Overview
`SLPlacementHybrid` is a volatility- and structure-aware stop-loss engine for trade execution agents. It integrates market structure, volatility (ATR), liquidity sweeps, and real-time spreads to generate robust stop-loss levels that align with institutional flow logic.

---

## ✅ Inputs

| Parameter | Type | Description |
|----------|------|-------------|
| `entry_price` | `float` | Price where trade is entered |
| `trade_direction` | `'BULLISH' | 'BEARISH'` | Direction of the trade |
| `initiating_swing_price` | `float` | M1 swing low/high that created CHoCH/BoS + FVG |
| `instrument_type` | `str` | e.g. 'Gold', 'Forex_Major' |
| `pip_value` | `float` | Price value of 1 pip for the asset |
| `std_pip_buffer` | `float` | Default: 2.0 (for normal instruments) |
| `vol_pip_extra` | `float` | Extra padding for high-volatility assets (e.g. Gold = 3.0) |

---

## 🔁 Engine Dependencies

| Engine | Method | Purpose |
|--------|--------|---------|
| `volatility_engine` | `get_atr_in_pips()` | Returns ATR as pip value (fallback minimum = 0.1) |
| `liquidity_engine` | `get_sweep_extreme(direction)` | Latest price wick from inducement/sweep |
| `spread_engine` | `get_current_spread_in_pips()` | Real-time spread to prevent premature hits |

---

## 🧩 Logic Flow

```yaml
1. Validate inputs:
   - Trade direction must be BULLISH or BEARISH
   - Swing point must be provided
2. Compute ATR-based buffer:
   - ATR fallback = 0.1 if dead/flat market
   - Add volatility extra if ATR > 20 or instrument = Gold
3. Add live spread to buffer:
   - Final Buffer = (std_pip_buffer + vol_extra) + spread_pips
4. Select base invalidation anchor:
   - BULLISH: min(structure_swing, sweep)
   - BEARISH: max(structure_swing, sweep)
5. Offset buffer from anchor:
   - BULLISH: SL = anchor - buffer_price
   - BEARISH: SL = anchor + buffer_price
6. Validate against entry (sanity check)

🧠 Module Blueprint: HybridSLPlanner (Stop-Loss Logic Core)

🔧 Purpose
Compute dynamic, context-aware stop-loss (SL) levels integrating:
Structure (swing logic from smc_enrichment_engine)
Volatility (ATR/price ranges via volatility_engine)
Liquidity sweep memory (liquidity_sweep_detector)
Microstructure & event filters (microstructure_filter, event_detector)
Trade risk alignment (risk_model, advanced_stoploss_lots_engine)
🔁 Input/Output Contract
Inputs:
- entry_price: float
- direction: 'long' | 'short'
- timeframe: 'M1' | 'M5' | 'M15'
- context_id: trade UUID or session

Outputs:
- sl_price: float
- method_trace: Dict with source of SL components
- sl_distance: float (pips)
- recommended_risk: float (%)
🔄 Component Flow
1. smc_enrichment_engine:
   - Get last structural CHoCH/BOS level
   - Tag as `structure_sl`

2. liquidity_sweep_detector:
   - Find last sweep extreme in direction
   - Output `sweep_buffer`

3. volatility_engine:
   - Compute ATR on timeframe (default 0.8x buffer)
   - Output `vol_buffer`

4. Combine:
   - SL = min(structure_sl, sweep_buffer) - vol_buffer (long)
   - SL = max(structure_sl, sweep_buffer) + vol_buffer (short)

5. risk_model + advanced_stoploss_lots_engine:
   - Calculate position sizing based on SL distance and equity
   - Output `lot_size`, `risk_score`
✅ Example Return Object
{
  "sl_price": 1.0863,
  "sl_distance": 14.3,
  "recommended_risk": 1.0,
  "method_trace": {
    "structure": 1.0874,
    "sweep": 1.0870,
    "volatility_buffer": 0.0007
  }
}
🧩 ZSI Integration Tags
sl_computation
risk_alignment_check
structure_vol_liquidity_blend
