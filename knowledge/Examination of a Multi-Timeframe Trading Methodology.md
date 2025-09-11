## 🧱 ContextAnalyzer – Multi-Timeframe Framework for Institutional Order Flow

### Objective
Establish a directional bias and trading narrative by synchronizing higher and lower timeframes through structure, liquidity, and institutional intent.

### Logic
- HTF (Daily, H4): Identify trend, strong highs/lows, premium/discount zones.
- MTF (H1/M15): Refine zones, observe price character approaching POIs.
- LTF (M15/M5/M1): Confirm entries using CHoCH/BoS after mitigation and liquidity sweep.

---

## 💧 LiquidityEngine – Inducement and Sweep Detection

### Objective
Detect engineered liquidity events and inducement patterns as precursors to valid setups.

### Logic
- Identify stops above/below swing points or session highs/lows (Asia range).
- Inducement: False moves to build liquidity before real intent.
- Sweep: Quick pierce of liquidity zone followed by mitigation and reversal.
- Trigger Sequence: Sweep → Mitigation → LTF Structure Break.

---

## 🔀 StructureValidator – BoS & CHoCH Logic

### Objective
Track market structure changes to define trend, momentum shifts, and entry confirmation.

### Logic
- BoS: Confirms trend continuation (new HH/LL in direction).
- CHoCH: First sign of reversal; break of counter-trend structure.
- HTF BoS: Sets overall bias.
- LTF CHoCH post-sweep: Entry trigger.

---

## 🧠 FVGLocator – Supply/Demand and Imbalance Zones

### Objective
Identify valid POIs using refined S/D logic, focusing on zones with strong institutional characteristics.

### Logic
- Demand: Last down candle before impulsive up move (and vice versa for supply).
- Must coincide with BoS or liquidity sweep.
- Zone refinement: HTF ➝ LTF narrowing.
- Mitigation must be followed by LTF CHoCH/BoS for trade validity.

---

## ⚠️ RiskManager – Logical Stop Loss and Targeting

### Objective
Control risk and define expectations through structurally sound stop/target placement.

### Logic
- SL: Below swing low (long) or above high (short) initiating the valid zone.
- Adjust SL for volatility (e.g., Gold 15–20 pips).
- TP1: First LTF structure/liquidity pool.
- TP2: HTF structural target or external range.
- Position sizing adjusts to SL to maintain fixed risk.

---

## 📊 ConfluenceStacker – Fib + Session Timing + HTF Sync

### Objective
Stack conditions (value, timing, volume context) to qualify setups.

### Logic
- Use 50% fib to define Premium (sells) or Discount (buys).
- Trade only if POI is in value zone.
- Align setup with session dynamics (Asia, London, NY).
- Prefer setups that initiate post-Asia sweep during London open.

---

## 🧩 Master Flow Sequence – MTF Liquidity Strategy

1. ContextAnalyzer → Establish HTF bias, define POIs, assess premium/discount  
2. LiquidityEngine → Identify inducement and sweep events  
3. StructureValidator → Confirm CHoCH or BoS post-mitigation  
4. FVGLocator → Refine and validate POI zone for entry  
5. RiskManager → Define SL and TP with position size logic  
6. ConfluenceStacker → Validate entry using fib, session, HTF flow  

✅ Issue 'mtf_trade_ready' tag if all align under institutional narrative framework.