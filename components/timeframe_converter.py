
import pandas as pd
import numpy as np

class TimeframeConverter:
    def __init__(self):
        self.timeframe_minutes = {
            'M1': 1,
            'M5': 5,
            'M15': 15,
            'M30': 30,
            'H1': 60,
            'H4': 240,
            'D1': 1440,
            'W1': 10080,
            'MN1': 43200
        }
    
    def generate_all_timeframes(self, df_m1):
        """Generate all possible timeframes from M1 data"""
        timeframes = {'M1': df_m1.copy()}
        
        # Determine which timeframes we can generate based on data availability
        total_minutes = (df_m1.index[-1] - df_m1.index[0]).total_seconds() / 60
        
        for tf_name, tf_minutes in self.timeframe_minutes.items():
            if tf_name == 'M1':
                continue
            
            # Only generate if we have enough data
            if total_minutes >= tf_minutes * 100:  # At least 100 bars
                try:
                    tf_data = self.resample_to_timeframe(df_m1, tf_name)
                    if len(tf_data) >= 100:
                        timeframes[tf_name] = tf_data
                except:
                    continue
        
        return timeframes
    
    def resample_to_timeframe(self, df, target_timeframe):
        """Resample data to a specific timeframe"""
        if target_timeframe not in self.timeframe_minutes:
            raise ValueError(f"Unknown timeframe: {target_timeframe}")
        
        # Get resample rule
        rule = self._get_resample_rule(target_timeframe)
        
        # Resample OHLCV data
        resampled = df.resample(rule).agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        })
        
        # Remove any NaN values
        resampled.dropna(inplace=True)
        
        return resampled
    
    def _get_resample_rule(self, timeframe):
        """Get pandas resample rule for timeframe"""
        minutes = self.timeframe_minutes[timeframe]
        
        if minutes < 60:
            return f'{minutes}T'
        elif minutes < 1440:
            return f'{minutes // 60}H'
        elif minutes == 1440:
            return 'D'
        elif minutes == 10080:
            return 'W'
        else:
            return 'M'
    
    def align_timeframes(self, timeframes_dict):
        """Align multiple timeframes to the same end time"""
        if not timeframes_dict:
            return timeframes_dict
        
        # Find the common end time
        end_times = [df.index[-1] for df in timeframes_dict.values()]
        common_end = min(end_times)
        
        # Align all timeframes
        aligned = {}
        for tf_name, df in timeframes_dict.items():
            aligned[tf_name] = df[df.index <= common_end].copy()
        
        return aligned
    
    def get_mtf_perspective(self, timeframes_dict, current_time=None):
        """Get multi-timeframe perspective at a specific time"""
        if current_time is None:
            current_time = min(df.index[-1] for df in timeframes_dict.values())
        
        perspective = {}
        
        for tf_name, df in timeframes_dict.items():
            # Get the last bar before or at current_time
            mask = df.index <= current_time
            if mask.any():
                last_idx = mask.sum() - 1
                perspective[tf_name] = {
                    'open': df['open'].iloc[last_idx],
                    'high': df['high'].iloc[last_idx],
                    'low': df['low'].iloc[last_idx],
                    'close': df['close'].iloc[last_idx],
                    'volume': df['volume'].iloc[last_idx],
                    'time': df.index[last_idx]
                }
        
        return perspective