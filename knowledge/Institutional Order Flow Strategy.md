🧠 ZSI Agent Framework — Institutional Order Flow Strategy

🧱 ContextBuilder – HTF Market Bias Logic
Objective: Establish multi-timeframe directional narrative.
Inputs: Daily, H4 price structure
Outputs: htf_bias_context, operational_range

Logic:
- Detect BoS on Daily → anchor directional bias
- Validate H4 alignment with Daily bias
- Define H4 operational range: last BoS leg
- Mark Premium/Discount zones within H4 range
💧 LiquidityProfiler – Engineered Trap Mapping
Objective: Identify institutional liquidity targets and inducement zones.
Inputs: Swing highs/lows, session highs/lows, trendlines
Outputs: liquidity_map, inducement_clusters

Logic:
- Detect retail confluence: equal highs/lows, trendline touches
- Session range: Asian session highs/lows as bait
- Map inducement ahead of POIs
- Score each zone by visibility and structural setup
🔍 POIIdentifier – Valid Zone Scanner
Objective: Pinpoint unmitigated POIs with imbalance origin.
Inputs: HTF BoS origin zones, refined candle logic
Outputs: poi_candidates, poi_type (Extreme/Decisional)

Logic:
- Supply = last buy-to-sell candle before bearish BoS
- Demand = last sell-to-buy candle before bullish BoS
- Tag as Extreme if origin of entire leg; Decisional if BoS pivot
- Must be unmitigated, within correct P/D context
🔀 StructureValidator – CHoCH/BoS Confirmation Module
Objective: Confirm structure shift aligned with HTF POI.
Inputs: M15 and M5 structure around POI
Outputs: confirmation_flag, m15_leg_range

Logic:
- CHoCH = first micro reversal after POI mitigation
- BoS = trend confirmation
- Capture impulsive move from POI → define M15 leg
- Validate if confirmation zone is in M15 P/D
🧠 EntryOrchestrator – Sweep/Trigger Agent
Objective: Time entry post-inducement and POI mitigation.
Inputs: M5/M1 inducement pattern + refined POI
Outputs: entry_zone, trigger_flag

Logic:
- Wait for inducement pattern just before POI (equal highs/lows, trendline)
- Entry only after liquidity sweep (wick + tap into POI)
- Optional: M1 BoS post-tap
⚠️ RiskModule – Dynamic SL/TP Structurer
Objective: Align stop/target logic with structural invalidation.
Inputs: entry zone, sweep point, HTF liquidity map
Outputs: sl_price, tp_targets, rr_score

Logic:
- SL: Below POI for longs / above POI for shorts
- TP1: First opposing internal liquidity (H4)
- TP2: HTF structural level or external range
- Optionally scale partials and runners based on HTF POIs
🕒 SessionTimingFilter – Killzone Validator
Objective: Synchronize trigger logic with institutional activity.
Inputs: Time of day, session high/low, Judas swing
Outputs: timing_score, session_bias

Logic:
- Prefer setups forming during London or NY Kill Zones
- Judas logic: Asia trap sweep → entry during London
- Time-align sweep, mitigation, and CHoCH within session structure
🔁 Master Execution Chain

1. ContextBuilder       → Bias & operational range
2. LiquidityProfiler    → Identify traps & targets
3. POIIdentifier        → Scan for valid unmitigated zones
4. StructureValidator   → Confirm LTF CHoCH/BoS post-mitigation
5. EntryOrchestrator    → Sweep + refined POI entry
6. RiskModule           → SL/TP logic based on structure/liquidity
7. SessionTimingFilter  → Enforce temporal alignment

✅ Emit `institutional_trade_ready` if all layers align with HTF narrative
Would you like this rendered into a .yaml, .md, or turned into Python agent classes inside the ZSI module tree?