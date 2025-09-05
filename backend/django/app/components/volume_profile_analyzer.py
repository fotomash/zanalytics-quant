
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
