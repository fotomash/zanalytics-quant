
import pandas as pd
import numpy as np

class MicrostructureAnalyzer:
    def __init__(self):
        pass

    def analyze(self, m1_df, ticks_df):
        """
        Performs a full microstructure analysis by correlating M1 bars with tick data.

        Args:
            m1_df (pd.DataFrame): The M1 OHLCV data.
            ticks_df (pd.DataFrame): The tick data.

        Returns:
            dict: A dictionary containing aggregated analysis results.
        """
        # Calculate tick-level metrics first
        ticks_with_delta = self._calculate_tick_delta(ticks_df)
        
        # Aggregate tick metrics to M1 bars
        aggregated_df = self._aggregate_ticks_to_bars(m1_df, ticks_with_delta)
        
        results = {
            'aggregated_metrics': aggregated_df,
            'cumulative_delta': aggregated_df['delta'].cumsum()
        }
        
        return results

    def _calculate_tick_delta(self, ticks_df):
        """
        Calculates the trade direction and delta for each tick.
        A common method is to classify ticks based on price movement.
        - Tick at ask: Buyer initiated (positive delta)
        - Tick at bid: Seller initiated (negative delta)
        - Tick between spread: Ambiguous
        
        A simpler proxy (the 'tick rule'):
        - Price moves up: Buyer initiated
        - Price moves down: Seller initiated
        """
        ticks = ticks_df.copy()
        
        # Use 'last' price if available, otherwise use mid-price
        price_col = 'last' if 'last' in ticks.columns and ticks['last'].sum() > 0 else 'mid_price'
        if price_col == 'mid_price':
            ticks['mid_price'] = (ticks['bid'] + ticks['ask']) / 2
            
        # Calculate price change to infer direction
        price_diff = ticks[price_col].diff()
        
        # Determine tick direction
        tick_direction = np.where(price_diff > 0, 1, np.where(price_diff < 0, -1, 0))
        
        # Use 'volume' if available and meaningful, otherwise use 'tickvol' or 1
        volume_col = 'volume'
        if 'volume' not in ticks.columns or ticks['volume'].sum() == 0:
            volume_col = 'tickvol' if 'tickvol' in ticks.columns and ticks['tickvol'].sum() > 0 else None
        
        if volume_col:
            ticks['delta'] = tick_direction * ticks[volume_col]
        else:
            # If no volume, delta is just the direction count
            ticks['delta'] = tick_direction
            
        return ticks

    def _aggregate_ticks_to_bars(self, m1_df, ticks_df):
        """
        Aggregates tick data metrics onto the M1 bar timeframe.
        """
        # Ensure m1_df index is datetime
        if not isinstance(m1_df.index, pd.DatetimeIndex):
            m1_df.index = pd.to_datetime(m1_df.index)
            
        # Create a new DataFrame to store results, aligned with m1_df
        aggregated_data = pd.DataFrame(index=m1_df.index)
        
        # Calculate metrics for each M1 bar
        bar_deltas = []
        tick_counts = []
        avg_spreads = []
        
        # Use resample for efficient aggregation
        resampler = ticks_df.resample('1Min')
        
        delta_sum = resampler['delta'].sum()
        tick_count = resampler.size()
        avg_spread = resampler['spread'].mean()
        
        # Align the resampled data with the M1 bar index
        aggregated_data['delta'] = delta_sum.reindex(m1_df.index, fill_value=0)
        aggregated_data['tick_count'] = tick_count.reindex(m1_df.index, fill_value=0)
        aggregated_data['avg_spread'] = avg_spread.reindex(m1_df.index).ffill() # Forward fill for bars with no ticks
        
        # Calculate Cumulative Delta within each bar
        aggregated_data['cumulative_delta'] = aggregated_data['delta'].cumsum()
        
        return aggregated_data
'''

with open('zanflow_dashboard/utils/microstructure_analyzer.py', 'w') as f:
    f.write(microstructure_analyzer)

print("1. Successfully created 'zanflow_dashboard/utils/microstructure_analyzer.py'.")