
# 🧠 LLM Analysis Directive: First Fair Value Gap (FVG) After 8AM London (M15 Only)

## 🎯 Objective
Detect and analyze the **first Fair Value Gap (FVG)** of each trading day using 15-minute chart data. This logic must align with ICT-style imbalance definitions and execute only **after 08:00 AM London time**, starting from **2024-06-03**.

---

## 📊 Technical FVG Definition

### ✅ Bullish FVG (Imbalance):
```
low[1] > high[2]
```
Occurs when the low of candle 2 is higher than the high of candle 3, indicating a bullish imbalance.

### ✅ Bearish FVG (Imbalance):
```
high[1] < low[2]
```
Occurs when the high of candle 2 is lower than the low of candle 3, indicating a bearish imbalance.

---

## ⏰ Time & Session Constraints

- Start processing from the **candle that closes at 08:00 AM London time**.
- Only execute logic for dates **on or after 2024-06-03**.
- Timezone offset: **UTC+1** during summer.
- Accept only data from the **15-minute timeframe**.

---

## 📐 Expected Analysis Output for Each Day

For the first FVG only:

- **Date** and **timestamp** of the FVG
- **Type**: Bullish or Bearish
- **Top & Bottom Price Boundaries** of the FVG
- **Was the FVG filled?** (true/false)
- **Time and nature of fill** (e.g., fast retrace, slow consolidation)
- **Market context** (trend bias, volume spike, structural confluence)
- **Outcome**: Did the market continue in FVG direction? Provide pip/percent move.

---

## ⚠️ Constraints

- Do **not** detect more than one FVG per day.
- FVG detection should only start **after 08:00 London**.
- Reject data if not on 15-minute timeframe.
- Provide warnings or fallbacks if data is missing or incorrectly formatted.

---

## 🛠️ Interoperability Notes

- Use this module alongside: `entry_executor_smc.py`, `copilot_orchestrator.py`, `scalp_filters.py`.
- Align logic with `zan_flow_1/2/3.md`, `v10.md`, and `Institutional Order Flow Strategy.md`.
- FVG detection influences **entry POIs** and **journal tagging** in orchestrator logic.

---

## 🧠 LLM Prompt Example

```markdown
Analyze the first FVG from June 10, 2024, after 08:00 London time on the 15m chart. 
Explain if it was bullish or bearish, the gap price range, if it got filled, and the market reaction.
```

---

## 🔄 Output Format Template
```markdown
### FVG Detected: 2024-06-10, 08:15 London
- Type: Bullish
- Range: 1.26450–1.26700
- Filled: Yes, at 10:30
- Context: Formed after London breakout; aligned with H1 uptrend; volume confirmed.
- Reaction: Price rallied +38 pips post-fill
```
