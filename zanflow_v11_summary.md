# ZANFLOW v11 Hybrid Strategy Execution — ISPTS Sequence

## ✅ Stage 1: ContextAnalyzer
Confirms macro context and structural bias. Aligns trade window with killzones. Checks Wyckoff Phase E (end of accumulation/distribution).

### Fallback:
If no clear phase or bias, mark setup as CONTEXT_REJECTED.

## ✅ Stage 2: LiquidityEngine
Detects inducement patterns. Validates sweep strength. Maps Points of Interest (POIs).

### Fallback:
If no inducement or sweep_score < threshold, label as POI_UNRELIABLE.

## ✅ Stage 3: StructureValidator
Looks for BoS or CHoCH following inducement. Scores based on distance, impulse, and volume.

### Fallback:
If no valid break found within N candles post-sweep, reject as INVALID_BREAK.

## ✅ Stage 4: FVGLocator
Confirms FVG aligns with structural POI. Ensures quality and liquidity overlap.

## ✅ Stage 5: RiskManager
Computes Risk:Reward ratio. Applies structural SL buffering. Validates SL-TP precision.

## ✅ Stage 6: ConfluenceStacker
Consolidates volatility, killzone timing, and volume profile. Outputs a normalized confluence score.

## ✅ Stage 7: Executor
Flags executable trades. Supports multi-agent isolation and journaling.

## 🧠 Memory & Observability
- `trace_id` used throughout for ZBAR logging.
- Predictive overlay (non-deterministic): maturity scoring, volatility metrics, spread instability, conflict detection.

## 🎯 Design Note
The predictive layer never vetoes trade decisions — it observes and logs context. All deterministic logic resides in the ISPTS stack.
