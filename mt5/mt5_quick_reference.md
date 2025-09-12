# MT5 Data Format Quick Reference

## 📊 Format Comparison Matrix

| Feature | Tick Data | M1/Candlestick Data |
|---------|-----------|---------------------|
| **File Pattern** | `SYMBOL_YYYYMMDD_HHMMSS_YYYYMMDD_HHMMSS.csv` | `SYMBOL_TIMEFRAME_YYYYMMDDHHMMSS_YYYYMMDDHHMMSS.csv` |
| **Time Precision** | Milliseconds (HH:MM:SS.mmm) | Seconds (HH:MM:SS) |
| **Price Fields** | BID, ASK, LAST | OPEN, HIGH, LOW, CLOSE |
| **Volume Fields** | VOLUME (actual trades) | TICKVOL (tick count), VOL (real volume) |
| **Special Fields** | FLAGS (2/4/6) | SPREAD (in points) |
| **Data Frequency** | Every price change | Fixed intervals (M1, M5, H1, etc.) |
| **Primary Use** | Microstructure analysis | Technical analysis |

## 🔍 Volume Field Disambiguation

### Tick Data
- **`<VOLUME>`**: Actual volume of the specific trade
  - ✅ Use for: Trade size analysis, large order detection
  - ❌ Not: Tick count or aggregated volume

### Candlestick Data  
- **`<TICKVOL>`**: Number of price updates in the period
  - ✅ Use for: Forex volume proxy, activity measurement
  - ❌ Not: Actual traded volume

- **`<VOL>`**: Real traded volume (if available)
  - ✅ Use for: Stocks, futures, commodities
  - ⚠️ Often 0 for forex pairs

## 🎯 Decision Tree for Volume Selection

```
Is it Tick Data?
├─ YES → Use <VOLUME>
└─ NO → Is it Candlestick Data?
         ├─ Is <VOL> > 0?
         │   ├─ YES → Use <VOL> (real volume)
         │   └─ NO → Use <TICKVOL> (tick count)
         └─ Invalid format
```

## 🚨 Common Confusion Points

1. **TICKVOL vs VOL**
   - TICKVOL = Count of price changes
   - VOL = Actual contracts/lots traded

2. **Tick Data VOLUME vs Candlestick VOL**
   - Different concepts despite similar names
   - Tick VOLUME = Single trade size
   - Candle VOL = Period aggregated volume

3. **FLAGS in Tick Data**
   - 2 = Bid price update only
   - 4 = Ask price update only  
   - 6 = Both Bid and Ask updated

## 📝 Processing Examples

### Tick Data Processing
```python
# Check FLAGS to determine valid prices
if row['<FLAGS>'] == 2:
    # Only BID is valid
    price = row['<BID>']
elif row['<FLAGS>'] == 4:
    # Only ASK is valid
    price = row['<ASK>']
else:  # FLAGS == 6
    # Both valid, use midpoint
    price = (row['<BID>'] + row['<ASK>']) / 2
```

### Candlestick Volume Selection
```python
# Smart volume selection
if df['<VOL>'].sum() > 0:
    volume = df['<VOL>']  # Real volume available
else:
    volume = df['<TICKVOL>']  # Use tick count as proxy
```

## ✅ Validation Checklist

- [ ] Identified data format (tick vs candle)
- [ ] Selected appropriate volume column
- [ ] Validated data integrity (OHLC relationships, FLAGS)
- [ ] Documented volume choice in processing metadata
- [ ] Handled NaN values appropriately
- [ ] Converted timestamps correctly
