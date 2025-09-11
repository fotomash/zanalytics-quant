## 🧱 ContextAnalyzer – Wyckoff P&F Framework for Zanzibar Inv Variant

### Objective
Blend Wyckoff Methodology with Point-and-Figure logic and the Zanzibar Inversion strategy for deep institutional alignment.

### Logic
- Identify TR via Wyckoff phases A–E.
- Confirm Spring or Shakeout to mark Phase C completion.
- Anchor count on Last Point of Support (LPS).
- Execute P&F count from right to left; use LPS level.
- Bar chart confirms SOS, LPS via volume and price behavior.

---

## 💧 LiquidityEngine – Wyckoff Spring/UTAD as Traps

### Objective
Use Phase C events (Spring, UTAD) to confirm liquidity events.

### Logic
- Spring = Stop-loss grab below TR support (accumulation).
- UTAD = False breakout above resistance (distribution).
- Verify via volume + price snapback.

---

## 🔀 StructureValidator – Phase Confirmation

### Objective
Ensure CHoCH aligns with phase progression and validates markup/markdown.

### Logic
- LPS CHoCH = shift from testing to breakout.
- Volume must increase with spread on SOS.
- Validate Phase D continuation through effort/result analysis.

---

## 🧠 FVGLocator – Effort Zones + P&F Projections

### Objective
Convert LPS breakout into FEG + P&F range for entries.

### Logic
- Impulse from LPS creates imbalance (FEG).
- P&F count = LPS + (Box × Columns × Reversal).
- Project conservative (LPS), aggressive (TR low), and median (midpoint) targets.

---

## ⚠️ RiskManager – Structural Anchors

### Objective
SL/TP logic based on P&F rules and Wyckoff phases.

### Logic
- SL: Just below Spring or TR low.
- TP: Layered targets based on count method.
- Use bar chart failure near max projection to exit.

---

## 📊 ConfluenceStacker – Volume + Phase + CLI Alignment

### Objective
Add confidence via volume confirmation, CLI automation, and JSON consistency.

### Logic
- CLI hook: `run_wyckoff_pf_analysis.py`
- JSON includes box, reversal, phase trigger, and stepping-stone logic.
- Validate Spring + SOS via bar chart volume fade and surge.

---

## 🧩 Master Flow Sequence (Wyckoff P&F)

1. ContextAnalyzer → Define TR, confirm Spring, SOS, LPS  
2. LiquidityEngine → Confirm Phase C as trap/sweep  
3. StructureValidator → CHoCH on LPS (Phase D start)  
4. FVGLocator → Map FEG and run P&F projection  
5. RiskManager → SL/TP from Spring/LPS anchors  
6. ConfluenceStacker → Validate via JSON + volume  

✅ Issue 'pf_trade_ready' tag if full sequence matches institutional flow and P&F count logic.