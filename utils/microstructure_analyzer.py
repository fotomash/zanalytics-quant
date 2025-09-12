
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
        
        # Ensure ticks_df index is datetime for resample
        if not isinstance(ticks_df.index, pd.DatetimeIndex):
            # Prefer an existing datetime-like column if present
            for col in ("timestamp", "datetime", "ts"):
                if col in ticks_df.columns:
                    ticks_df = ticks_df.set_index(pd.to_datetime(ticks_df[col]))
                    break
            else:
                # As a last resort, attempt to convert the existing index
                ticks_df.index = pd.to_datetime(ticks_df.index)
        # Normalize tick index using timestamp-like columns if available
        dt_col = next((col for col in ("timestamp", "datetime", "ts") if col in ticks_df.columns), None)
        if dt_col:
            ticks_df.index = pd.to_datetime(ticks_df[dt_col])
            ticks_df.drop(columns=[dt_col], inplace=True)
        else:
            ticks_df.index = pd.to_datetime(ticks_df.index)

        # Sort to ensure proper chronological resampling
        ticks_df = ticks_df.sort_index()

        # Ensure spread column exists
        if 'spread' not in ticks_df.columns:
            if {'ask', 'bid'}.issubset(ticks_df.columns):
                ticks_df['spread'] = (ticks_df['ask'] - ticks_df['bid']).abs()
            else:
                ticks_df['spread'] = 0.0

        # Ensure m1_df index is datetime
        if not isinstance(m1_df.index, pd.DatetimeIndex):
            m1_df.index = pd.to_datetime(m1_df.index)

        # Create a new DataFrame to store results, aligned with m1_df
        aggregated_data = pd.DataFrame(index=m1_df.index)

        # Use resample for efficient aggregation on the normalized index
        resampler = ticks_df.resample('1Min')

        # Align the resampled data with the M1 bar index
        aggregated_data['delta'] = resampler['delta'].sum().reindex(m1_df.index, fill_value=0)
        aggregated_data['tick_count'] = resampler.size().reindex(m1_df.index, fill_value=0)
        aggregated_data['avg_spread'] = (
            resampler['spread'].mean().reindex(m1_df.index).ffill()
        )  # Forward fill for bars with no ticks

        # Calculate Cumulative Delta within each bar
        aggregated_data['cumulative_delta'] = aggregated_data['delta'].cumsum()

        return aggregated_data
