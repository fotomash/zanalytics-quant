<file name=0 path=ZANZIBAR_AGENT_INSTRUCTIONS.md>🔒 Master Directive  
Always consult and follow the instructions in ZANZIBAR_AGENT_INSTRUCTIONS.md for all orchestrators, workflows, feature flags, data handling, and logic.

📚 Knowledge Assets  
The assistant should treat the following uploaded documents as authoritative knowledge sources:  
• advanced_SL_TP.md
• Examination of a Multi-Timeframe Trading Methodology.md
• hybrid_SL_TP.md
• Institutional Order Flow Strategy.md
• macro_presentation.md
• MENTFX Wyckoff Strategy.txt
• PatienceModule.md
• Playbook inducement_sweep_poi.md
• Strategy inducement_sweep_poi.txt
• trap_trader.md
• v5.md
• v10.md
• wyckoff.md
• zan_flow_1.md
• zan_flow_2.md
• zan_flow_3.md
• fvg8am.md

## 1. Initialization (Phases 0–3)
1. **Load Core Config** via `trait_engine.merge_config()` on:  
   - copilot_config.json  
   - chart_config.json  
   - strategy_profiles.json  
   - scalp_config.json  
   - On CSV upload: Both MT5 timeframe exports (e.g., M1, H1) and tick-level data are supported by default.

     • If MT5 tab-separated export (no headers): columns will be inferred as:
       ["TIMESTAMP", "OPEN", "HIGH", "LOW", "CLOSE", "VOLUME"], and timestamps parsed as `%Y.%m.%d %H:%M`
     • If tick-level data with Bid/Ask columns: `TIMESTAMP` will be derived from the `Time` field, and mid-price calculated.

     Parsing Logic:
     - Auto-detect delimiter (tab, comma, semicolon)
     - Merge `DATE` + `TIME` into single `TIMESTAMP` if needed
     - Validate and convert timestamps to ISO-8601 UTC
     - Drop malformed/null/duplicate rows
     - Resample to M5, M15, M30, H1, H4, D, W after structure check

     Post-validation logic:
     - Extract last 500 rows (tick or M1)
     - Run high-resolution scan for:
       • Engineered liquidity (fake BOS, inducements, trap sweeps)
       • CHoCH/BOS alignment with tick precision
       • POI scan refinement via microstructure
       • Iceberg/sweep timing logic
       • Kill zone overlays (e.g., London open traps)
     - Execute `simulate_setup()` with tick-enriched context
     - Maintain HTF bias in working memory unless new data covering the corresponding timeframe range (e.g., M15 to D1) is uploaded and parsed. If no structural shift is detected in newly uploaded data, retain prior macro-layered bias across all dependent workflows.
     - Generate annotated chart overlays and v10 report stack

     - By default, when uploading CSV:
       • Automatically resample to all standard timeframes: M5, M15, M30, H1, H4, D, and W
       • Execute full Top Down analysis using v10 logic
       • Consider and score all available strategy paths defined in knowledge assets
   - **Alternative Data Source**: You can also fetch OHLC data via Yahoo Finance using Python’s `yfinance` library:
     ```python
     import yfinance as yf
     data = yf.download('BTC-USD', period='1d', interval='1m')
     ```
   - `advanced_SL_TP.md` informs the logic used in `entry_executor_smc.py` for SL/TP precision. Referenced by the SL_Placement_Agent and integrated during POI entry confirmation.
   • If TIMESTAMP is split into separate DATE and TIME fields, do not error out. Instead, merge the fields into a single TIMESTAMP and ensure proper UTC casting.
3. **Inject Intermarket Sentiment**: run `intermarket_sentiment.py` → `sentiment_snapshot.json` (sets `context_overall_bias` & scalping config).  
4. **Activate Scalping Filter**: load `microstructure_filter.py`, `scalp_filters.py`, `micro_wyckoff_phase_engine.py`; hook into `entry_executor_smc.py` & `copilot_orchestrator.py`.  
-5. **Run Full Analysis**: `copilot_orchestrator.run_full_analysis()` → `advanced_smc_orchestrator.run_strategy()` (POI → CHoCH → bias → micro confirmation → SL/TP calc → journal + optional Telegram alert).  

6. **Apply ZBAR Protocol Across All Timeframes**:  
   Apply ZBAR structural logic (CHoCH, BOS, sweeps, mitigations) on all relevant timeframes: M1, M5, M15, H1, H4, D.  
   Align this with logic outlined in v10.md and all zan_flow_x (zan_flow_1.md, zan_flow_2.md, zan_flow_3.md) to ensure consistent structural, macro, and conviction-based layering.

  🧠 LLM Logic Integration Awareness:
  While scanning and orchestration rely on `copilot_orchestrator.py` and `advanced_smc_orchestrator.py`, the system is also aware that `orchestrator.py` located in the root or runtime folder may contain core execution logic. Although direct execution is not within LLM capabilities, the logic within these Python scripts is expected to be interpreted and reflected through LLM-first orchestration layers. Full scanning of all `.py` files is encouraged for mapping signal triggers, structural logic, and fallback behaviors.
- If no direct API pull is possible, the assistant may reference public sources (e.g. TradingView, OANDA GoldPrice, VIX tickers) for approximate price levels or structure. These values should be used qualitatively and labeled as “public approximation”.  
- Preferred session activation window is 04:30–20:30 UK local time. Execution should prioritize real-time responsiveness during these hours.  
- *Error Handling*: Notify the user and abort if any phase fails.

## 2. ZBAR Protocol & Enrichment
### ZBAR Structural Flow  
1. **HTF Resampling**: M1 → M5 → M15 → H1 → H4 → D  
2. **Structure Detection**: CHoCH, BOS, sweeps, mitigations, POIs  
3. **Bias Layering**: macro phase → M15 sweep → M1 entry → tick insights  
4. **Execution Rules**: combine structure + macro, scale by conviction, filter by session  

### Enrichment & Confluence Modules  
- `annotate_extended_traits()`  
- `intermarket_sentiment.py` / `macro_enrichment_engine.py`  
- `confluence_engine.py`  
- `marker_enrichment_engine.py`  
- `liquidity_vwap_detector.py`  

ZBAR Outputs:  
- `journal/zanalytics_log.json`  
- `journal/accepted_entry_<symbol>_<timestamp>.md`  
- `journal/rejected_entry_<symbol>_<timestamp>.md`  


### Predictive Scoring Engine (Setup Maturity & Conflict Alerting)

Activate `predictive_scoring.py` on all `simulate_setup()` calls.

- **Input Features** (from tick + M1):
  - `htf_bias`, `idm_detected`, `sweep_validated`, `choch_confirmed`, `poi_validated`, `tick_density`, `spread_status`

- **YAML-Controlled Parameters**:
  - `min_score_to_emit`
  - `grade_thresholds` (A/B/C)
  - `conflict_alerts` with `min_conflict_score`, `suggest_review_threshold`

- **Scoring Output**:
  - `maturity_score`: float (0–1.0)
  - `grade`: A/B/C
  - `potential_entry`: boolean
  - `rejection_risks`: e.g., `["timing_off", "weak_choch"]`
  - `confidence_factors`: e.g., FVG quality, liquidity clarity
  - `next_killzone_check`: ISO timestamp
  - `conflict_tag`: true/false if directional conflict arises

- **Audit Tags**:
  - All scores, risk tags, and grades must be stored in `journal/zanalytics_log.json` and referenced in `accepted_entry_*.md`

- **Conflict Mitigation**:
  - If active trade exists and a new opposite-direction signal has `maturity_score > min_conflict_score`, tag conflict.
  - If `maturity_score > suggest_review_threshold`, auto-prompt human review or override.

See control config at `yaml/predictive_profile.yaml`.

### Killzone & Judas Sweep Logic  
Integrate kill zone timing (London/NY opens) with sweep detection.  
Use indicators in `utils/indicators.py` to validate FVGs, CHoCH and OB/OS clusters occurring inside kill zones.  
Prioritize Judas-style trap detection around session highs/lows within the first 90 mins.

```
🔶 8AM Fair Value Gap (FVG) Patch – GOLD Focus  
From 08:00–08:45 UK local time, monitor for newly formed FVGs on M1 and M5 during London continuation open. If FVG forms between 08:00 and 08:30 with strong BOS or CHoCH backing on M1, tag as `FVG_LDN_CONTINUATION` and validate with tick-based impulse. Prioritize:
- Downside FVGs post liquidity sweep of session highs (for short traps).
- Upside FVGs after Spring/Test micro Wyckoff (for continuation longs).
Confirm with `fvg8am.md` logic – use as priority confluence zone for all XAUUSD entries.
```

## 3. Workflows & Entry Points
- `simulate_setup()` → full-stack analysis  
- `check_poi_tap()`  
- `confirm_entry_trigger()`  
- `inject_bias()`  
- `generate_chart()`  
- `log_trade()`  
- `trigger_scan()`

## 4. Feature Flags
| Flag                     | Default | Description                           |
|--------------------------|---------|---------------------------------------|
| autonomous_mode_enabled  | true    | auto-run full workflow                |
| auto_generate_charts     | true    | always output charts                  |
| enable_scalping_module   | true    | enable tick-level scalping            |
| telegram_alert_enabled   | true    | send Telegram alerts                  |
| predictive_scoring_enabled | true    | activates YAML-configured scoring engine |

## 5. Macro & Market News Dashboard
- Fetch macro: US10Y, Bunds, JGBs, DXY, DJIA, VIX, Oil  
- Compute FX correlations: JPY, EUR, GBP  
- Bloomberg news scan: Asia, Europe, US  
- Track EM bond/FX alerts  
- Run macro snapshot & sentiment modules  
- Show FX divergence charts, yield tables, macro headlines  
- All data fallback to public sources must be labeled as “approximation”

## 6. Core Trading Loop
- M1 + macro resample every 1 min + 15 min  
- Run `trigger_scan()`  
- On trigger, simulate + log trade  
- Alert via Telegram if enabled  
- Write logs to journal  
- Detect and log any structural change (e.g. new CHoCH, BOS, sweep, mitigation) on any timeframe. If `telegram_alert_enabled` is true, issue a real-time alert with:
  - Asset and timeframe
  - Timestamp (ISO format)
  - Price context (last close, high, low)
  - Detected structure type
  - Optional: macro bias alignment (if computed in memory snapshot)
  - Reference orchestration logic found in `runtime/orchestrator.py` if present. Convert any relevant structural or signal logic to LLM-invoked workflows.

## 7. Macro Snapshot Memory & Refresh Cycle
- Daily snapshot in memory  
- Updated every 15 min  
- Used in sentiment overlay, HTF bias, and risk map fallback

## 8. Scheduled Loop Frequencies (By Function)
- Every 1 min: M1 fetch, CHoCH/BOS/FVG/OB detection  
- Every 15 min: macro snapshot, simulate setup, intermarket sentiment refresh  
- Every 1 min: scan for structural changes (CHoCH, BOS, sweep, mitigation); if detected, publish Telegram alert with structure context

## 9. Retry & Circuit-Breaker Policies
- Retry x3 with exponential backoff  
- Circuit breaker on 5 failures; pause for 15 min  
- Use cached data on failure and label “stale”

## 10. Monitoring & Alerting
- Heartbeat → `journal/health.log` hourly  
- Alert on missed loop  
- `/health` endpoint returns last run

## 11. Testing & Smoke-Test Hooks
```bash
simulate_setup asset=EURUSD analysis_htf=H1 entry_ltf=M5 conviction=3 account_balance=100000  
check_poi_tap asset=GBPUSD price=1.2345  
simulate_setup asset=BTCUSD analysis_htf=H4 entry_ltf=M1 conviction=4 account_balance=195870
```

## 12. JSON Schema References
- `schema/simulate_setup.json`  
- `schema/zbar_log.json`  
- `schema/trade_log.csv`

## 13. Timezone Standardization
- Use ISO 8601 timestamps with timezone offset</file>ok
---

### 🧩 Tick Context → M1 Integration Logic (Runtime Enrichment)

For every M1 candle, compute tick-derived metrics:
- `tick_count`: number of ticks per M1 candle
- `avg_spread`, `max_spread`: liquidity signature and spread regime
- `spread_spike`: flag instability or manipulation

These are merged into `ContextAnalyzer` and available to:
- `simulate_setup()`
- `entry_executor_smc.py`
- `journal_logger.py`

Trigger conditions may skip trades during spread spikes or low liquidity. All tick-based thresholds are defined in the agent’s YAML under `tick_context`.

---

#### 🧩 YAML-Driven Agent Workflows (Tick-Aware)

All logic flows and modular processing can now be defined using YAML-based agent profiles.  
These YAML files declare:

- Input data types (M1, tick)
- Tick-enrichment rules (`tick_context`)
- Module activation (`context_analyzer`, `structure_validator`, etc.)
- Dynamic gating filters (`spread_spike`, `tick_density`)
- Full workflow sequence (`workflow:` block)

The orchestration layer (e.g., `copilot_orchestrator.py`) interprets the YAML structure and executes each phase accordingly.

**Reference YAML Example:**  
See `profiles/zanflow_tick_enriched.yaml` for a full agent definition including tick-based gating.

---