# Tick Data Manipulation Detection Prompt

## 🎯 OBJECTIVE
Analyze tick data for algorithmic manipulation patterns using minimal tokens.

## 📊 INPUT FORMAT
```csv
datetime,spread,spread_change,time_diff,flags
```

## 🔍 DETECTION RULES (Priority Order)

### 1. SPREAD MANIPULATION
- Normal spread: 0.25-0.35 (for XAUUSD)
- Red flag: Spread > 2x normal
- Critical: Sudden spread widening before price moves

### 2. QUOTE STUFFING
- Normal update rate: >100ms between ticks
- Red flag: >50% updates <50ms apart
- Critical: Burst of updates with no price change

### 3. STOP HUNTING
- Normal reversal rate: 40-50%
- Red flag: >60% reversal rate
- Critical: V-shaped moves with spread widening

### 4. LAYERING/SPOOFING
- Look for: Asymmetric bid/ask updates (FLAGS pattern)
- Red flag: Repeated one-sided updates
- Critical: Price moves opposite to quote pressure

## 📝 ANALYSIS TEMPLATE

```
MANIPULATION SCORE: [0-10]
TYPE: [SPREAD_ABUSE|QUOTE_STUFF|STOP_HUNT|SPOOFING|CLEAN]
EVIDENCE: [One line summary]
ACTION: [AVOID|WAIT|SAFE]
```

## 🚀 EXAMPLE ANALYSIS

Input:
```
2025-05-23 08:30:01.220,0.33,0.01,0.328,6
2025-05-23 08:30:01.231,0.33,0.00,0.011,6
2025-05-23 08:30:01.552,0.33,0.00,0.321,6
```

Output:
```
MANIPULATION SCORE: 7
TYPE: QUOTE_STUFF
EVIDENCE: 200 updates <50ms, no price improvement
ACTION: WAIT
```
