
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