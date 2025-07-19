# Create SMC Analyzer
# smc_analyzer = '''"""
# Smart Money Concepts Analyzer
# Implements institutional trading concepts and order flow analysis
# """

import pandas as pd
import numpy as np
from scipy.signal import find_peaks

class SMCAnalyzer:
    def __init__(self):
        self.liquidity_zones = []
        self.order_blocks = []
        self.fair_value_gaps = []
        self.market_structure = []
    
    def analyze(self, df):
        """Run complete SMC analysis"""
        results = {
            'liquidity_zones': self.identify_liquidity_zones(df),
            'order_blocks': self.identify_order_blocks(df),
            'fair_value_gaps': self.identify_fair_value_gaps(df),
            'market_structure': self.analyze_market_structure(df),
            'liquidity_sweeps': self.detect_liquidity_sweeps(df),
            'displacement': self.detect_displacement(df),
            'inducement': self.detect_inducement(df)
        }
        
        return results
    
    def identify_liquidity_zones(self, df, lookback=50):
        """Identify buy-side and sell-side liquidity zones"""
        liquidity_zones = []
        
        # Rolling highs and lows
        rolling_high = df['high'].rolling(window=lookback).max()
        rolling_low = df['low'].rolling(window=lookback).min()
        
        # Find equal highs/lows (liquidity pools)
        for i in range(lookback, len(df)):
            # Buy-side liquidity (above equal highs)
            high_count = (abs(df['high'].iloc[i-lookback:i] - df['high'].iloc[i]) < df['high'].iloc[i] * 0.0001).sum()
            if high_count >= 2:
                liquidity_zones.append({
                    'type': 'BSL',  # Buy-side liquidity
                    'level': df['high'].iloc[i],
                    'strength': high_count / lookback,
                    'index': i,
                    'time': df.index[i]
                })
            
            # Sell-side liquidity (below equal lows)
            low_count = (abs(df['low'].iloc[i-lookback:i] - df['low'].iloc[i]) < df['low'].iloc[i] * 0.0001).sum()
            if low_count >= 2:
                liquidity_zones.append({
                    'type': 'SSL',  # Sell-side liquidity
                    'level': df['low'].iloc[i],
                    'strength': low_count / lookback,
                    'index': i,
                    'time': df.index[i]
                })
        
        # Remove duplicates and sort by strength
        unique_zones = []
        for zone in liquidity_zones:
            is_duplicate = False
            for existing in unique_zones:
                if existing['type'] == zone['type'] and abs(existing['level'] - zone['level']) < zone['level'] * 0.001:
                    is_duplicate = True
                    break
            if not is_duplicate:
                unique_zones.append(zone)
        
        return sorted(unique_zones, key=lambda x: x['strength'], reverse=True)
    
    def identify_order_blocks(self, df, min_move=0.002):
        """Identify bullish and bearish order blocks"""
        order_blocks = []
        
        for i in range(10, len(df) - 10):
            # Bullish order block (last down candle before up move)
            if df['close'].iloc[i] < df['open'].iloc[i]:  # Down candle
                # Check for significant up move after
                future_high = df['high'].iloc[i+1:i+10].max()
                if (future_high - df['close'].iloc[i]) / df['close'].iloc[i] > min_move:
                    order_blocks.append({
                        'type': 'bullish',
                        'start': df['low'].iloc[i],
                        'end': df['high'].iloc[i],
                        'index': i,
                        'time': df.index[i],
                        'strength': (future_high - df['close'].iloc[i]) / df['close'].iloc[i]
                    })
            
            # Bearish order block (last up candle before down move)
            elif df['close'].iloc[i] > df['open'].iloc[i]:  # Up candle
                # Check for significant down move after
                future_low = df['low'].iloc[i+1:i+10].min()
                if (df['close'].iloc[i] - future_low) / df['close'].iloc[i] > min_move:
                    order_blocks.append({
                        'type': 'bearish',
                        'start': df['high'].iloc[i],
                        'end': df['low'].iloc[i],
                        'index': i,
                        'time': df.index[i],
                        'strength': (df['close'].iloc[i] - future_low) / df['close'].iloc[i]
                    })
        
        return sorted(order_blocks, key=lambda x: x['strength'], reverse=True)[:20]
    
    def identify_fair_value_gaps(self, df, min_gap_size=0.0005):
        """Identify fair value gaps (imbalances)"""
        fvgs = []
        
        for i in range(2, len(df)):
            # Bullish FVG
            gap_size = df['low'].iloc[i] - df['high'].iloc[i-2]
            if gap_size > 0 and gap_size / df['close'].iloc[i] > min_gap_size:
                fvgs.append({
                    'type': 'bullish',
                    'top': df['low'].iloc[i],
                    'bottom': df['high'].iloc[i-2],
                    'size': gap_size,
                    'index': i,
                    'time': df.index[i],
                    'filled': False
                })
            
            # Bearish FVG
            gap_size = df['low'].iloc[i-2] - df['high'].iloc[i]
            if gap_size > 0 and gap_size / df['close'].iloc[i] > min_gap_size:
                fvgs.append({
                    'type': 'bearish',
                    'top': df['low'].iloc[i-2],
                    'bottom': df['high'].iloc[i],
                    'size': gap_size,
                    'index': i,
                    'time': df.index[i],
                    'filled': False
                })
        
        # Check if FVGs have been filled
        for fvg in fvgs:
            idx = fvg['index']
            if idx < len(df) - 1:
                future_prices = df.iloc[idx+1:]
                if fvg['type'] == 'bullish':
                    if (future_prices['low'] <= fvg['bottom']).any():
                        fvg['filled'] = True
                else:
                    if (future_prices['high'] >= fvg['top']).any():
                        fvg['filled'] = True
        
        return fvgs
    
    def analyze_market_structure(self, df):
        """Analyze market structure breaks and shifts"""
        structure = []
        
        # Find swing highs and lows
        highs, _ = find_peaks(df['high'].values, distance=10)
        lows, _ = find_peaks(-df['low'].values, distance=10)
        
        # Combine and sort by index
        swings = []
        for h in highs:
            swings.append({'type': 'high', 'index': h, 'price': df['high'].iloc[h]})
        for l in lows:
            swings.append({'type': 'low', 'index': l, 'price': df['low'].iloc[l]})
        
        swings.sort(key=lambda x: x['index'])
        
        # Analyze structure
        for i in range(2, len(swings)):
            current = swings[i]
            prev = swings[i-1]
            prev_prev = swings[i-2]
            
            # Bullish structure break
            if (current['type'] == 'high' and prev['type'] == 'low' and 
                prev_prev['type'] == 'high' and current['price'] > prev_prev['price']):
                structure.append({
                    'type': 'bullish_break',
                    'index': current['index'],
                    'time': df.index[current['index']],
                    'price': current['price'],
                    'previous_high': prev_prev['price']
                })
            
            # Bearish structure break
            elif (current['type'] == 'low' and prev['type'] == 'high' and 
                  prev_prev['type'] == 'low' and current['price'] < prev_prev['price']):
                structure.append({
                    'type': 'bearish_break',
                    'index': current['index'],
                    'time': df.index[current['index']],
                    'price': current['price'],
                    'previous_low': prev_prev['price']
                })
        
        return structure
    
    def detect_liquidity_sweeps(self, df):
        """Detect liquidity sweeps (stop hunts)"""
        sweeps = []
        liquidity_zones = self.identify_liquidity_zones(df)
        
        for zone in liquidity_zones:
            zone_idx = zone['index']
            if zone_idx < len(df) - 20:
                # Check for sweep and reversal
                if zone['type'] == 'BSL':  # Buy-side liquidity
                    # Look for price going above and then reversing
                    future_data = df.iloc[zone_idx:zone_idx+20]
                    max_idx = future_data['high'].idxmax()
                    max_price = future_data['high'].max()
                    
                    if max_price > zone['level']:
                        # Check for reversal
                        after_max = future_data.loc[max_idx:]
                        if len(after_max) > 5:
                            reversal = after_max['close'].iloc[-1] < zone['level']
                            if reversal:
                                sweeps.append({
                                    'type': 'buy_side_sweep',
                                    'level': zone['level'],
                                    'sweep_high': max_price,
                                    'time': max_idx,
                                    'reversal_confirmed': True
                                })
                
                elif zone['type'] == 'SSL':  # Sell-side liquidity
                    # Look for price going below and then reversing
                    future_data = df.iloc[zone_idx:zone_idx+20]
                    min_idx = future_data['low'].idxmin()
                    min_price = future_data['low'].min()
                    
                    if min_price < zone['level']:
                        # Check for reversal
                        after_min = future_data.loc[min_idx:]
                        if len(after_min) > 5:
                            reversal = after_min['close'].iloc[-1] > zone['level']
                            if reversal:
                                sweeps.append({
                                    'type': 'sell_side_sweep',
                                    'level': zone['level'],
                                    'sweep_low': min_price,
                                    'time': min_idx,
                                    'reversal_confirmed': True
                                })
        
        return sweeps
    
    def detect_displacement(self, df, threshold=2.0):
        """Detect strong directional moves (displacement)"""
        displacements = []
        
        # Calculate candle ranges and average
        candle_ranges = df['high'] - df['low']
        avg_range = candle_ranges.rolling(window=20).mean()
        
        for i in range(20, len(df)):
            current_range = candle_ranges.iloc[i]
            
            # Check for displacement
            if current_range > threshold * avg_range.iloc[i]:
                # Determine direction
                if df['close'].iloc[i] > df['open'].iloc[i]:
                    direction = 'bullish'
                else:
                    direction = 'bearish'
                
                displacements.append({
                    'type': direction,
                    'index': i,
                    'time': df.index[i],
                    'range': current_range,
                    'ratio': current_range / avg_range.iloc[i],
                    'open': df['open'].iloc[i],
                    'close': df['close'].iloc[i]
                })
        
        return displacements
    
    def detect_inducement(self, df):
        """Detect inducement (liquidity grab before reversal)"""
        inducements = []
        structure = self.analyze_market_structure(df)
        
        for i in range(1, len(structure)):
            current = structure[i]
            prev = structure[i-1]
            
            # Look for minor break followed by major reversal
            if current['type'] == 'bullish_break' and i < len(structure) - 1:
                next_move = structure[i+1]
                if next_move['type'] == 'bearish_break':
                    # Potential bullish inducement
                    inducements.append({
                        'type': 'bullish_inducement',
                        'fake_break': current,
                        'reversal': next_move,
                        'time': current['time']
                    })
            
            elif current['type'] == 'bearish_break' and i < len(structure) - 1:
                next_move = structure[i+1]
                if next_move['type'] == 'bullish_break':
                    # Potential bearish inducement
                    inducements.append({
                        'type': 'bearish_inducement',
                        'fake_break': current,
                        'reversal': next_move,
                        'time': current['time']
                    })
        
        return inducements
