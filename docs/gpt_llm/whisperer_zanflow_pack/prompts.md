# 🧠 ZSI_XANFLOW — GPT Scenario Triggers (Master Runtime v0.15+)

Prompts are valid across **all runtime sessions** — not tied to any legacy architecture or time filter. They function as
**predictive probes**, **logic validators**, and **execution stress-tests** within the `main_orchestrator.py` logic.

These prompts are optimized for developing, testing, and expanding the multi-agent trading logic embedded within
`GEMINI.zip`. Use them to activate specific design flows, simulate state decisions, or refine pipeline logic.

---

## 🛠️ Strategy Debug & Validation

- "Simulate a full ISPTS flow using gold_swing.yaml and show rejection logic."
- "What trace_tags and rejection reasons would fire if the CHoCH fails?"
- "Can you replay the last kill zone POI scan and list potential FVGs rejected?"

---

## 🧩 Modular Logic Enhancement

- "Show how to enrich liquidity_engine.py to detect engineered trendline sweeps."
- "Extend context_analyzer.py to include HTF EMA alignment as a gating rule."
- "Refactor fvg_locator.py to support breaker-blocks alongside FVGs."

---

## 🧬 Agent Profile Design

- "Draft a new agent YAML for scalp_reversal using M1 inducement traps only."
- "What would a dual-timeframe profile look like with M1 entries + H1 context?"
- "How do I include tick_density and spread_spike from tick context in agent logic?"

---

## 📊 Journaling & ZBAR Introspection

- "Show a ZBAR log sample for a trap_trade_ready setup with full maturity trace."
- "Can ZBAR support grading heuristics like ‘A/B/C’ outcomes? Add it."
- "What would a failed entry FVG log look like in JSON + markdown?"

---

## 🔁 Orchestration & Multi-Agent Flow

- "Build a two-agent cascade where Agent A handles context, Agent B handles entry."
- "Show main_orchestrator.py routing logic if structure_validator is delayed async."
- "Can we create a fallback-agent trigger if RR < 2.0? Propose YAML + logic diff."

---

## 🔧 GPT Instruction (Embedded Runtime)

When loaded into the GEMINI context, GPT should:

- Always check `prompts.md` for scenario triggers or user queries.
- Auto-suggest prompt completions when user is idle or uncertain.
- Log prompt usage into session trace for future ZBAR replay.

⸻

🔍 POI Qualification & Refinement
• “Scan recent POIs and rank them by confluence with sweep + HTF structure.”
• “How can I auto-classify POIs into breaker vs mitigation zones dynamically?”
• “Generate a YAML flag logic for rejecting wicks with low volume confirmation.”

⸻

📈 Volatility & Dynamic Risk
• “Integrate ATR and session_range buffers into SL logic for smart-RR control.”
• “Show how to adjust TP1 and TP2 based on evolving HTF volatility zones.”
• “Propose YAML+Python to delay entries if spread exceeds dynamic threshold.”

⸻

🔄 Session Awareness & Temporal Filters
• “Simulate NYO kill zone setup and overlay with Judas swing logic.”
• “Create a time_filter block to ignore setups outside 07:00–12:00 UTC.”
• “What logic detects and avoids setups during low-volatility drift periods?”

⸻

🔧 Failure Mode Analysis & Rejection Study
• “Replay last 10 trades and log all rejection reasons + module that rejected.”
• “What are the most frequent setup blockers across 30 POI scans?”
• “Add logic to warn if CHoCH is structurally valid but lacks momentum.”

⸻

🧱 Predictive Evolution & Maturity Metrics
• “Simulate how maturity_score evolves over time for a pending sweep setup.”
• “Add FVG_watchlist support with entry_delay heuristics.”
• “Propose journal replay YAML to validate future alignment scoring across sessions.”

⸻

### 📡 Live Setup Triage & Prediction Injection

- "Evaluate setup_state memory for early entry viability."
- "What trace_tags would fire for an entry pre-confirmation?"
- "Inject POI scan from 15m with expected structure mismatch — predict maturity_score."

⸻

### 📘 Architectural Proposal & Agent Rewiring

- "Suggest modular split of context vs entry logic inside main_orchestrator.py."
- "Convert existing `fvg_locator.py` into async callable for parallel agent use."
- "Design fallback-agent reroute logic for rejection_case: ‘liquidity_missing’."
