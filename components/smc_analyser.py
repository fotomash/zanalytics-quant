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
'''

with open('zanflow_dashboard/utils/smc_analyzer.py', 'w') as f:
    f.write(smc_analyzer)
print("Created smc_analyzer.py")

# Create Wyckoff Analyzer
wyckoff_analyzer = '''"""
Wyckoff Method Analyzer
Implements Wyckoff methodology for market phase analysis
"""

import pandas as pd
import numpy as np
from scipy.signal import find_peaks

class WyckoffAnalyzer:
    def __init__(self):
        self.phases = ['Accumulation', 'Markup', 'Distribution', 'Markdown']
        self.events = []
    
    def analyze(self, df):
        """Run complete Wyckoff analysis"""
        results = {
            'current_phase': self.identify_current_phase(df),
            'events': self.detect_wyckoff_events(df),
            'volume_analysis': self.analyze_volume_patterns(df),
            'spring_upthrust': self.detect_springs_upthrusts(df),
            'sos_sow': self.detect_sos_sow(df),
            'trading_ranges': self.identify_trading_ranges(df),
            'composite_operator': self.analyze_composite_operator(df)
        }
        
        return results
    
    def identify_current_phase(self, df, lookback=100):
        """Identify the current Wyckoff phase"""
        if len(df) < lookback:
            return "Insufficient data"
        
        recent_data = df.tail(lookback)
        
        # Calculate key metrics
        price_range = recent_data['high'].max() - recent_data['low'].min()
        avg_price = recent_data['close'].mean()
        price_position = (recent_data['close'].iloc[-1] - recent_data['low'].min()) / price_range
        
        # Volume analysis
        avg_volume = recent_data['volume'].mean()
        recent_volume = recent_data['volume'].tail(20).mean()
        volume_trend = recent_volume / avg_volume
        
        # Trend analysis
        sma_20 = recent_data['close'].rolling(20).mean()
        sma_50 = recent_data['close'].rolling(50).mean() if len(recent_data) >= 50 else sma_20
        
        # Phase determination logic
        if price_position < 0.3 and volume_trend > 1.2:
            # Low in range with increasing volume
            return "Accumulation"
        elif price_position > 0.7 and volume_trend > 1.2:
            # High in range with increasing volume
            return "Distribution"
        elif len(sma_20) > 0 and len(sma_50) > 0:
            if sma_20.iloc[-1] > sma_50.iloc[-1] and recent_data['close'].iloc[-1] > sma_20.iloc[-1]:
                return "Markup"
            elif sma_20.iloc[-1] < sma_50.iloc[-1] and recent_data['close'].iloc[-1] < sma_20.iloc[-1]:
                return "Markdown"
        
        return "Transitional"
    
    def detect_wyckoff_events(self, df):
        """Detect specific Wyckoff events"""
        events = []
        
        # Find potential events
        for i in range(20, len(df) - 5):
            # Preliminary Support (PS)
            if self._is_preliminary_support(df, i):
                events.append({
                    'type': 'PS',
                    'description': 'Preliminary Support',
                    'index': i,
                    'time': df.index[i],
                    'price': df['low'].iloc[i]
                })
            
            # Selling Climax (SC)
            if self._is_selling_climax(df, i):
                events.append({
                    'type': 'SC',
                    'description': 'Selling Climax',
                    'index': i,
                    'time': df.index[i],
                    'price': df['low'].iloc[i]
                })
            
            # Automatic Rally (AR)
            if self._is_automatic_rally(df, i):
                events.append({
                    'type': 'AR',
                    'description': 'Automatic Rally',
                    'index': i,
                    'time': df.index[i],
                    'price': df['high'].iloc[i]
                })
            
            # Secondary Test (ST)
            if self._is_secondary_test(df, i):
                events.append({
                    'type': 'ST',
                    'description': 'Secondary Test',
                    'index': i,
                    'time': df.index[i],
                    'price': df['low'].iloc[i]
                })
        
        return events
    
    def _is_preliminary_support(self, df, i):
        """Check if current bar is preliminary support"""
        # Look for first meaningful support after downtrend
        if i < 50:
            return False
        
        # Check for downtrend
        prev_trend = df['close'].iloc[i-50:i].mean() > df['close'].iloc[i-25:i].mean()
        
        # Check for support with volume
        is_low = df['low'].iloc[i] == df['low'].iloc[i-10:i+10].min()
        high_volume = df['volume'].iloc[i] > df['volume'].iloc[i-20:i].mean() * 1.5
        
        return prev_trend and is_low and high_volume
    
    def _is_selling_climax(self, df, i):
        """Check if current bar is selling climax"""
        # Extreme volume and price drop
        volume_spike = df['volume'].iloc[i] > df['volume'].iloc[i-20:i].mean() * 2.5
        price_drop = (df['close'].iloc[i] - df['close'].iloc[i-5]) / df['close'].iloc[i-5] < -0.02
        
        # Followed by reversal
        if i < len(df) - 5:
            reversal = df['close'].iloc[i+5] > df['close'].iloc[i]
            return volume_spike and price_drop and reversal
        
        return False
    
    def _is_automatic_rally(self, df, i):
        """Check if current bar is automatic rally"""
        # Rally after selling climax
        if i < 10:
            return False
        
        # Check for recent low
        recent_low_idx = df['low'].iloc[i-10:i].idxmin()
        if recent_low_idx in df.index:
            recent_low_pos = df.index.get_loc(recent_low_idx)
            
            # Check for rally
            rally = (df['high'].iloc[i] - df['low'].iloc[recent_low_pos]) / df['low'].iloc[recent_low_pos] > 0.02
            decreasing_volume = df['volume'].iloc[i] < df['volume'].iloc[recent_low_pos]
            
            return rally and decreasing_volume
        
        return False
    
    def _is_secondary_test(self, df, i):
        """Check if current bar is secondary test"""
        # Test of previous low with less volume
        if i < 30:
            return False
        
        # Find previous significant low
        prev_low_idx = df['low'].iloc[i-30:i-5].idxmin()
        if prev_low_idx in df.index:
            prev_low = df['low'].loc[prev_low_idx]
            prev_volume = df['volume'].loc[prev_low_idx]
            
            # Check if testing previous low
            testing_low = abs(df['low'].iloc[i] - prev_low) / prev_low < 0.002
            less_volume = df['volume'].iloc[i] < prev_volume * 0.7
            
            return testing_low and less_volume
        
        return False
    
    def detect_springs_upthrusts(self, df):
        """Detect springs and upthrusts"""
        springs_upthrusts = []
        
        # Identify trading ranges first
        ranges = self.identify_trading_ranges(df)
        
        for range_info in ranges:
            start_idx = range_info['start']
            end_idx = range_info['end']
            
            if end_idx >= len(df) - 5:
                continue
            
            # Look for springs (false breakdown)
            range_low = df['low'].iloc[start_idx:end_idx].min()
            for i in range(end_idx, min(end_idx + 20, len(df) - 5)):
                if df['low'].iloc[i] < range_low * 0.998:  # Break below
                    # Check for reversal
                    if df['close'].iloc[i+5] > range_low:
                        springs_upthrusts.append({
                            'type': 'Spring',
                            'index': i,
                            'time': df.index[i],
                            'range_low': range_low,
                            'spring_low': df['low'].iloc[i],
                            'reversal_confirmed': True
                        })
            
            # Look for upthrusts (false breakout)
            range_high = df['high'].iloc[start_idx:end_idx].max()
            for i in range(end_idx, min(end_idx + 20, len(df) - 5)):
                if df['high'].iloc[i] > range_high * 1.002:  # Break above
                    # Check for reversal
                    if df['close'].iloc[i+5] < range_high:
                        springs_upthrusts.append({
                            'type': 'Upthrust',
                            'index': i,
                            'time': df.index[i],
                            'range_high': range_high,
                            'upthrust_high': df['high'].iloc[i],
                            'reversal_confirmed': True
                        })
        
        return springs_upthrusts
    
    def detect_sos_sow(self, df):
        """Detect Sign of Strength (SOS) and Sign of Weakness (SOW)"""
        sos_sow = []
        
        for i in range(20, len(df) - 5):
            # Sign of Strength - price advance on increasing volume
            if df['close'].iloc[i] > df['close'].iloc[i-1]:
                price_change = (df['close'].iloc[i] - df['close'].iloc[i-5]) / df['close'].iloc[i-5]
                volume_increase = df['volume'].iloc[i] > df['volume'].iloc[i-20:i].mean() * 1.3
                
                if price_change > 0.01 and volume_increase:
                    sos_sow.append({
                        'type': 'SOS',
                        'index': i,
                        'time': df.index[i],
                        'price': df['close'].iloc[i],
                        'strength': price_change * (df['volume'].iloc[i] / df['volume'].iloc[i-20:i].mean())
                    })
            
            # Sign of Weakness - price decline on increasing volume
            elif df['close'].iloc[i] < df['close'].iloc[i-1]:
                price_change = (df['close'].iloc[i] - df['close'].iloc[i-5]) / df['close'].iloc[i-5]
                volume_increase = df['volume'].iloc[i] > df['volume'].iloc[i-20:i].mean() * 1.3
                
                if price_change < -0.01 and volume_increase:
                    sos_sow.append({
                        'type': 'SOW',
                        'index': i,
                        'time': df.index[i],
                        'price': df['close'].iloc[i],
                        'weakness': abs(price_change) * (df['volume'].iloc[i] / df['volume'].iloc[i-20:i].mean())
                    })
        
        return sos_sow
    
    def identify_trading_ranges(self, df, min_length=20):
        """Identify trading ranges (consolidation areas)"""
        ranges = []
        
        i = 0
        while i < len(df) - min_length:
            # Check if we're in a range
            window = df.iloc[i:i+min_length]
            high_range = window['high'].max()
            low_range = window['low'].min()
            avg_price = window['close'].mean()
            
            # Calculate range as percentage
            range_pct = (high_range - low_range) / avg_price
            
            # If range is tight enough, extend it
            if range_pct < 0.05:  # 5% range
                end_idx = i + min_length
                
                # Extend range while price stays within bounds
                while end_idx < len(df):
                    if (df['high'].iloc[end_idx] <= high_range * 1.01 and 
                        df['low'].iloc[end_idx] >= low_range * 0.99):
                        end_idx += 1
                    else:
                        break
                
                if end_idx - i >= min_length:
                    ranges.append({
                        'start': i,
                        'end': end_idx,
                        'high': high_range,
                        'low': low_range,
                        'duration': end_idx - i,
                        'start_time': df.index[i],
                        'end_time': df.index[end_idx-1] if end_idx < len(df) else df.index[-1]
                    })
                
                i = end_idx
            else:
                i += 1
        
        return ranges
    
    def analyze_volume_patterns(self, df):
        """Analyze volume patterns in context of price action"""
        patterns = {
            'effort_vs_result': [],
            'volume_dry_up': [],
            'volume_surge': []
        }
        
        for i in range(20, len(df)):
            # Effort vs Result
            price_change = abs(df['close'].iloc[i] - df['open'].iloc[i]) / df['open'].iloc[i]
            volume_ratio = df['volume'].iloc[i] / df['volume'].iloc[i-20:i].mean()
            
            # High effort, low result (potential reversal)
            if volume_ratio > 2 and price_change < 0.002:
                patterns['effort_vs_result'].append({
                    'index': i,
                    'time': df.index[i],
                    'type': 'high_effort_low_result',
                    'volume_ratio': volume_ratio,
                    'price_change': price_change
                })
            
            # Volume dry up (potential end of move)
            if volume_ratio < 0.5:
                patterns['volume_dry_up'].append({
                    'index': i,
                    'time': df.index[i],
                    'volume_ratio': volume_ratio
                })
            
            # Volume surge
            if volume_ratio > 3:
                patterns['volume_surge'].append({
                    'index': i,
                    'time': df.index[i],
                    'volume_ratio': volume_ratio,
                    'price_direction': 'up' if df['close'].iloc[i] > df['open'].iloc[i] else 'down'
                })
        
        return patterns
    
    def analyze_composite_operator(self, df):
        """Analyze potential composite operator behavior"""
        co_analysis = {
            'accumulation_signs': [],
            'distribution_signs': [],
            'manipulation_signs': []
        }
        
        # Look for accumulation signs
        ranges = self.identify_trading_ranges(df)
        for range_info in ranges:
            if range_info['end'] < len(df) - 10:
                # Check what happens after range
                breakout_idx = range_info['end']
                if df['close'].iloc[breakout_idx + 10] > range_info['high'] * 1.02:
                    co_analysis['accumulation_signs'].append({
                        'range': range_info,
                        'breakout_confirmed': True,
                        'type': 'range_accumulation'
                    })
        
        # Look for distribution signs
        for i in range(50, len(df) - 20):
            # Check for high volume at tops
            if df['high'].iloc[i] == df['high'].iloc[i-50:i+50].max():
                if df['volume'].iloc[i] > df['volume'].iloc[i-50:i].mean() * 2:
                    co_analysis['distribution_signs'].append({
                        'index': i,
                        'time': df.index[i],
                        'price': df['high'].iloc[i],
                        'type': 'high_volume_top'
                    })
        
        return co_analysis
'''

with open('zanflow_dashboard/utils/wyckoff_analyzer.py', 'w') as f:
    f.write(wyckoff_analyzer)
print("Created wyckoff_analyzer.py")

# Create Volume Profile Analyzer
volume_profile = '''"""
Volume Profile Analyzer
Analyzes volume distribution across price levels
"""

import pandas as pd
import numpy as np

class VolumeProfileAnalyzer:
    def __init__(self):
        self.profile = None
        self.poc = None  # Point of Control
        self.value_area = None
    
    def analyze(self, df, num_bins=50):
        """Create and analyze volume profile"""
        results = {
            'profile': self.create_volume_profile(df, num_bins),
            'poc': self.find_poc(),
            'value_area': self.calculate_value_area(),
            'hvn_lvn': self.identify_hvn_lvn(),
            'naked_poc': self.find_naked_poc(df),
            'volume_gaps': self.find_volume_gaps()
        }
        
        return results
    
    def create_volume_profile(self, df, num_bins=50):
        """Create volume profile from OHLCV data"""
        # Define price range
        price_min = df['low'].min()
        price_max = df['high'].max()
        price_range = price_max - price_min
        
        # Create bins
        bins = np.linspace(price_min, price_max, num_bins + 1)
        bin_centers = (bins[:-1] + bins[1:]) / 2
        
        # Initialize volume profile
        volume_profile = np.zeros(num_bins)
        
        # Distribute volume across price levels
        for idx, row in df.iterrows():
            # Find bins that this candle spans
            candle_min = row['low']
            candle_max = row['high']
            candle_volume = row['volume']
            
            # Distribute volume evenly across the candle's range
            for i in range(num_bins):
                bin_low = bins[i]
                bin_high = bins[i + 1]
                
                # Check if this bin overlaps with the candle
                if bin_high >= candle_min and bin_low <= candle_max:
                    # Calculate overlap
                    overlap_low = max(bin_low, candle_min)
                    overlap_high = min(bin_high, candle_max)
                    overlap_ratio = (overlap_high - overlap_low) / (candle_max - candle_min)
                    
                    # Add proportional volume
                    volume_profile[i] += candle_volume * overlap_ratio
        
        # Store profile
        self.profile = pd.DataFrame({
            'price': bin_centers,
            'volume': volume_profile,
            'bin_low': bins[:-1],
            'bin_high': bins[1:]
        })
        
        return self.profile
    
    def find_poc(self):
        """Find Point of Control (price with highest volume)"""
        if self.profile is None:
            return None
        
        poc_idx = self.profile['volume'].idxmax()
        self.poc = {
            'price': self.profile.loc[poc_idx, 'price'],
            'volume': self.profile.loc[poc_idx, 'volume'],
            'bin_low': self.profile.loc[poc_idx, 'bin_low'],
            'bin_high': self.profile.loc[poc_idx, 'bin_high']
        }
        
        return self.poc
    
    def calculate_value_area(self, percentage=0.70):
        """Calculate value area (70% of volume)"""
        if self.profile is None or self.poc is None:
            return None
        
        total_volume = self.profile['volume'].sum()
        target_volume = total_volume * percentage
        
        # Start from POC and expand
        poc_idx = self.profile['volume'].idxmax()
        included_indices = [poc_idx]
        current_volume = self.profile.loc[poc_idx, 'volume']
        
        # Expand from POC
        while current_volume < target_volume:
            # Find next highest volume bin not yet included
            remaining = self.profile[~self.profile.index.isin(included_indices)]
            if remaining.empty:
                break
            
            next_idx = remaining['volume'].idxmax()
            included_indices.append(next_idx)
            current_volume += remaining.loc[next_idx, 'volume']
        
        # Calculate value area bounds
        included_indices.sort()
        vah_idx = included_indices[-1]  # Value Area High
        val_idx = included_indices[0]   # Value Area Low
        
        self.value_area = {
            'vah': self.profile.loc[vah_idx, 'bin_high'],
            'val': self.profile.loc[val_idx, 'bin_low'],
            'percentage': current_volume / total_volume,
            'volume': current_volume
        }
        
        return self.value_area
    
    def identify_hvn_lvn(self, threshold=1.5):
        """Identify High Volume Nodes and Low Volume Nodes"""
        if self.profile is None:
            return None
        
        avg_volume = self.profile['volume'].mean()
        
        hvn = self.profile[self.profile['volume'] > avg_volume * threshold].copy()
        lvn = self.profile[self.profile['volume'] < avg_volume / threshold].copy()
        
        return {
            'hvn': hvn[['price', 'volume']].to_dict('records'),
            'lvn': lvn[['price', 'volume']].to_dict('records')
        }
    
    def find_naked_poc(self, df):
        """Find naked POCs (untested POCs from previous periods)"""
        if self.poc is None:
            return []
        
        naked_pocs = []
        
        # For simplicity, we'll check if current POC has been revisited
        poc_price = self.poc['price']
        current_price = df['close'].iloc[-1]
        
        # Check if price has moved away from POC
        if abs(current_price - poc_price) / poc_price > 0.02:  # 2% away
            # Check if POC has been tested after initial formation
            # This is simplified - in practice, you'd track POCs over time
            naked_pocs.append({
                'price': poc_price,
                'formed_at': df.index[len(df)//2],  # Approximate
                'distance_from_current': abs(current_price - poc_price) / poc_price
            })
        
        return naked_pocs
    
    def find_volume_gaps(self, gap_threshold=0.3):
        """Find gaps in volume profile (potential support/resistance)"""
        if self.profile is None:
            return []
        
        avg_volume = self.profile['volume'].mean()
        gaps = []
        
        for i in range(1, len(self.profile) - 1):
            current_vol = self.profile.iloc[i]['volume']
            
            # Check if this is a low volume area between high volume areas
            if current_vol < avg_volume * gap_threshold:
                prev_vol = self.profile.iloc[i-1]['volume']
                next_vol = self.profile.iloc[i+1]['volume']
                
                if prev_vol > avg_volume and next_vol > avg_volume:
                    gaps.append({
                        'price': self.profile.iloc[i]['price'],
                        'gap_start': self.profile.iloc[i]['bin_low'],
                        'gap_end': self.profile.iloc[i]['bin_high'],
                        'volume': current_vol
                    })
        
        return gaps
'''

with open('zanflow_dashboard/utils/volume_profile.py', 'w') as f:
    f.write(volume_profile)
print("Created volume_profile.py")