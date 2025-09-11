🧠 ZSI Institutional Strategy – High-Level Execution Blueprint

Title: Inducement–Sweep–POI Trap System (ISPTS v3)
Purpose: Engineer precision entries around institutional liquidity footprints using a sequenced, multi-layer agent model.
Execution Level: Trade-grade, real-time agent-compatible (LLM + Python modularity)
🧱 1. ContextAnalyzer – Structural Range & Regime Definition

Function:
Anchor directional logic using HTF-confirmed strong swing points, derived from liquidity events.
Deep Logic Flow:
Parse price action into confirmed Strong Highs/Lows (sweep + BoS)
Build operational range: last Strong High ↔ Strong Low
Generate derived zones:
Discount zone (0–50% fib): only allow longs
Premium zone (50–100% fib): only allow shorts
Equilibrium (EQ): potential partial TP or breakout trap zone
Label context: htf_bias = bullish | bearish
Triggers:
range_initialized + bias_set
💧 2. LiquidityEngine – IDM Trap + Sweep Validator

Function:
Diagnose engineered liquidity traps using inducement-sweep-rejection pattern logic.
Deep Logic Flow:
Inducement = visually obvious retail trap (EQH, OB, trendline break, fake CHoCH)
Sweep = sudden price pierce + reversal wick (high momentum → low volume snap)
Must detect session-based targeting: Asian High/Low → London Sweep
Sweep must:
Exist within HTF bias structure
Occur pre-Kill Zone or within
Triggers:
idm_detected, sweep_validated
🔀 3. StructureValidator – Post-Sweep Entry Gate

Function:
Enable entry logic only if price validates direction via structural shift post-sweep.
Deep Logic Flow:
Entry only after sweep → CHoCH (LTF) or BoS (continuation)
CHoCH confirms new intent
BoS confirms strength
Timeframe sequencing:
M5/M1 CHoCH: primary entry
M15 BoS: bias reinforcement
Triggers:
choch_confirmed, entry_window_open
🧠 4. FVGLocator – Micro-Zone Precision Entry Module

Function:
Map and rank POIs for entry based on market imbalance and reversal anatomy.
Deep Logic Flow:
Candidate POIs:
OB (last up/down candle before impulse)
FVG (BISI/SIBI)
BB (flipped failed OB)
MB (failure swing rejection + revisit)
Rejection Wick (pinbar sweep entry)
Refine entry: always on reaction + structure, not just price
Triggers:
poi_validated, entry_prepped
⚠️ 5. RiskManager – SL/TP Engine with Structure & Liquidity Awareness

Function:
Define risk edge relative to structure, sweep origin, and volatility.
Deep Logic Flow:
SL: beyond wick sweep point (structure-proven invalidation)
TP1 = IRL: internal swing, FVG
TP2 = ERL: external Strong High/Low
Optional trailing on micro CHoCH + move SL to BE post TP1
Triggers:
risk_frame_set, tp_targets_mapped
📊 6. ConfluenceStacker – MTF Validator + Timing Filter

Function:
Score trades based on time bias, volatility alignment, and institutional rhythm.
Deep Logic Flow:
Confirm Kill Zone + AMD cycle phase (A/M/D)
Ensure LTF setup inside HTF narrative
Validate:
HTF bias zone → M5 inducement → M1 confirmation
Trigger filter tag: session_match + cycle_match
🔁 Master Execution Chain

1. ContextAnalyzer      → HTF bias + operative range
2. LiquidityEngine      → Detect inducement and confirm sweep
3. StructureValidator   → Confirm structure shift (CHoCH/BoS)
4. FVGLocator           → Lock refined POI
5. RiskManager          → SL/TP aligned with sweep + structure
6. ConfluenceStacker    → Validate via session + time filter

✅ Emit: 'trap_trade_ready'

🔧 Integration Pipeline:

Agent	Output Tags	Dependencies
ContextAnalyzer	range_initialized, bias_set	swing tracker, fib tool
LiquidityEngine	sweep_validated, idm_detected	volume engine, kill zone map
StructureValidator	choch_confirmed	microstructure_engine
FVGLocator	poi_validated	fvg_detector
RiskManager	risk_frame_set, tp_targets_mapped	hybrid_sl_engine
ConfluenceStacker	session_match, cycle_match	session_filter, volatility map
