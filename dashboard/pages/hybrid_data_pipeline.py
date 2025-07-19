import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Optional, Union
import asyncio
import json
from dataclasses import dataclass
import pyarrow.parquet as pq
import pyarrow as pa
from concurrent.futures import ThreadPoolExecutor

@dataclass
class DataConfig:
    """Configuration for data pipeline"""
    raw_data_path: str = "./data/raw"
    enriched_data_path: str = "./data/enriched"
    enable_realtime: bool = True
    batch_size: int = 1000
    enrichment_level: str = "full"  # "minimal", "standard", "full"

class HybridDataPipeline:
    """
    Hybrid data pipeline that supports both real-time and batch processing
    """

    def __init__(self, config: DataConfig):
        self.config = config
        self.executor = ThreadPoolExecutor(max_workers=4)

        # Create directories
        Path(config.raw_data_path).mkdir(parents=True, exist_ok=True)
        Path(config.enriched_data_path).mkdir(parents=True, exist_ok=True)

    async def ingest_tick(self, tick_data: Dict) -> Dict:
        """
        Ingest tick data with minimal enrichment for real-time use
        """
        symbol = tick_data['symbol']
        timestamp = tick_data['timestamp']

        # Minimal enrichment (fast calculations only)
        enriched = {
            **tick_data,
            'mid_price': (tick_data['bid'] + tick_data['ask']) / 2,
            'spread': tick_data['ask'] - tick_data['bid'],
            'spread_bps': (tick_data['ask'] - tick_data['bid']) / tick_data['bid'] * 10000
        }

        # Store raw data
        await self._append_to_parquet(
            f"{self.config.raw_data_path}/{symbol}_ticks_{datetime.now().date()}.parquet",
            tick_data
        )

        # If real-time enrichment is enabled, do minimal enrichment
        if self.config.enable_realtime:
            enriched['enrichment_level'] = 'minimal'
            enriched['enriched_at'] = datetime.now().isoformat()

        return enriched

    async def get_enriched_data(
        self, 
        symbol: str, 
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        enrichment_level: str = "standard"
    ) -> pd.DataFrame:
        """
        Get enriched data - either from cache or compute on-demand
        """
        # Check for pre-enriched data
        enriched_file = f"{self.config.enriched_data_path}/{symbol}_{enrichment_level}.parquet"

        if Path(enriched_file).exists():
            # Load pre-enriched data
            df = pd.read_parquet(enriched_file)

            # Filter by time if needed
            if start_time:
                df = df[df['timestamp'] >= start_time]
            if end_time:
                df = df[df['timestamp'] <= end_time]

            # Check if enrichment is fresh enough
            if self._is_enrichment_fresh(df):
                return df

        # Otherwise, load raw data and enrich on-demand
        raw_df = await self._load_raw_data(symbol, start_time, end_time)

        # Enrich based on requested level
        if enrichment_level == "minimal":
            return self._minimal_enrichment(raw_df)
        elif enrichment_level == "standard":
            return self._standard_enrichment(raw_df)
        else:  # full
            return self._full_enrichment(raw_df)

    def _minimal_enrichment(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Minimal enrichment - just spreads and mid prices
        """
        df['mid_price'] = (df['bid'] + df['ask']) / 2
        df['spread'] = df['ask'] - df['bid']
        df['spread_bps'] = df['spread'] / df['bid'] * 10000
        df['enrichment_level'] = 'minimal'
        return df

    def _standard_enrichment(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Standard enrichment - includes basic technical indicators
        """
        # Start with minimal
        df = self._minimal_enrichment(df)

        # Add rolling metrics
        df['vwap'] = (df['mid_price'] * df['volume']).cumsum() / df['volume'].cumsum()
        df['rsi'] = self._calculate_rsi(df['mid_price'])
        df['volatility'] = df['mid_price'].pct_change().rolling(window=100).std()

        # Simple microstructure
        df['effective_spread'] = df['spread'].rolling(window=50).mean()
        df['volume_imbalance'] = (df['bid_volume'] - df['ask_volume']).rolling(window=20).sum()

        df['enrichment_level'] = 'standard'
        return df

    def _full_enrichment(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Full enrichment - includes all microstructure metrics
        """
        # Start with standard
        df = self._standard_enrichment(df)

        # Advanced microstructure
        df['realized_spread'] = self._calculate_realized_spread(df)
        df['price_impact'] = self._calculate_price_impact(df)
        df['liquidity_score'] = self._calculate_liquidity_score(df)
        df['toxicity_score'] = self._calculate_toxicity_score(df)

        # Market regime
        df['market_regime'] = self._identify_market_regime(df)
        df['trend_strength'] = self._calculate_trend_strength(df)

        df['enrichment_level'] = 'full'
        return df

    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """Calculate RSI"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))

    def _calculate_realized_spread(self, df: pd.DataFrame, lag: int = 5) -> pd.Series:
        """Calculate realized spread"""
        return (df['mid_price'] - df['mid_price'].shift(lag)).abs()

    def _calculate_price_impact(self, df: pd.DataFrame) -> pd.Series:
        """Calculate price impact using regression"""
        # Simplified Kyle's lambda
        volume_imbalance = df['bid_volume'] - df['ask_volume']
        price_changes = df['mid_price'].pct_change()

        # Rolling regression coefficient
        impact = pd.Series(index=df.index, dtype=float)
        window = 50

        for i in range(window, len(df)):
            x = volume_imbalance.iloc[i-window:i].values
            y = price_changes.iloc[i-window:i].values

            # Remove NaN values
            mask = ~(np.isnan(x) | np.isnan(y))
            if mask.sum() > 10:
                x, y = x[mask], y[mask]
                if np.std(x) > 0:
                    impact.iloc[i] = np.corrcoef(x, y)[0, 1] * np.std(y) / np.std(x)

        return impact.fillna(0)

    def _calculate_liquidity_score(self, df: pd.DataFrame) -> pd.Series:
        """Calculate liquidity score"""
        avg_spread = df['spread'].rolling(window=50).mean()
        avg_volume = (df['bid_volume'] + df['ask_volume']).rolling(window=50).mean()
        return 1 / (avg_spread * np.sqrt(1/avg_volume))

    def _calculate_toxicity_score(self, df: pd.DataFrame) -> pd.Series:
        """Calculate toxicity score"""
        returns = df['mid_price'].pct_change()
        volume = df['bid_volume'] + df['ask_volume']
        volume_weighted_returns = (returns * volume).rolling(window=50).mean()
        return volume_weighted_returns.abs() * 10000

    def _identify_market_regime(self, df: pd.DataFrame) -> pd.Series:
        """Identify market regime"""
        returns = df['mid_price'].pct_change()
        volatility = returns.rolling(window=50).std()
        trend = df['mid_price'].rolling(window=100).apply(
            lambda x: np.polyfit(np.arange(len(x)), x, 1)[0]
        )

        regime = pd.Series(index=df.index, dtype=str)
        regime[trend > 0.0001] = 'trending_up'
        regime[trend < -0.0001] = 'trending_down'
        regime[(trend >= -0.0001) & (trend <= 0.0001)] = 'ranging'

        # Adjust for volatility
        high_vol = volatility > volatility.rolling(window=500).mean() * 1.5
        regime[high_vol & (regime == 'ranging')] = 'volatile_ranging'

        return regime.fillna('unknown')

    def _calculate_trend_strength(self, df: pd.DataFrame) -> pd.Series:
        """Calculate trend strength"""
        prices = df['mid_price']

        def trend_strength(x):
            if len(x) < 2:
                return 0
            x_range = np.arange(len(x))
            slope, intercept = np.polyfit(x_range, x, 1)
            y_pred = slope * x_range + intercept
            r_squared = 1 - np.sum((x - y_pred)**2) / np.sum((x - x.mean())**2)
            return r_squared * np.sign(slope)

        return prices.rolling(window=100).apply(trend_strength)

    async def _append_to_parquet(self, filepath: str, data: Dict):
        """Append data to parquet file efficiently"""
        df_new = pd.DataFrame([data])

        if Path(filepath).exists():
            # Read existing data
            df_existing = pd.read_parquet(filepath)
            # Append new data
            df_combined = pd.concat([df_existing, df_new], ignore_index=True)
            # Write back
            df_combined.to_parquet(filepath, index=False)
        else:
            # Create new file
            df_new.to_parquet(filepath, index=False)

    async def _load_raw_data(
        self, 
        symbol: str, 
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> pd.DataFrame:
        """Load raw data from parquet files"""
        pattern = f"{self.config.raw_data_path}/{symbol}_*.parquet"
        files = list(Path(self.config.raw_data_path).glob(f"{symbol}_*.parquet"))

        if not files:
            return pd.DataFrame()

        # Load all relevant files
        dfs = []
        for file in files:
            df = pd.read_parquet(file)
            if 'timestamp' in df.columns:
                df['timestamp'] = pd.to_datetime(df['timestamp'])

                # Filter by time range if specified
                if start_time and df['timestamp'].max() < start_time:
                    continue
                if end_time and df['timestamp'].min() > end_time:
                    continue

                if start_time:
                    df = df[df['timestamp'] >= start_time]
                if end_time:
                    df = df[df['timestamp'] <= end_time]

            dfs.append(df)

        if not dfs:
            return pd.DataFrame()

        return pd.concat(dfs, ignore_index=True).sort_values('timestamp')

    def _is_enrichment_fresh(self, df: pd.DataFrame, max_age_minutes: int = 5) -> bool:
        """Check if enrichment is fresh enough"""
        if 'enriched_at' not in df.columns:
            return False

        last_enrichment = pd.to_datetime(df['enriched_at'].max())
        age = datetime.now() - last_enrichment

        return age.total_seconds() < max_age_minutes * 60

    async def batch_enrich_historical(self, symbol: str, enrichment_level: str = "full"):
        """
        Batch process historical data with full enrichment
        Run this periodically (e.g., every hour) to pre-compute enriched data
        """
        print(f"Starting batch enrichment for {symbol} at {enrichment_level} level...")

        # Load all raw data
        raw_df = await self._load_raw_data(symbol)

        if raw_df.empty:
            print(f"No raw data found for {symbol}")
            return

        # Enrich based on level
        if enrichment_level == "minimal":
            enriched_df = self._minimal_enrichment(raw_df)
        elif enrichment_level == "standard":
            enriched_df = self._standard_enrichment(raw_df)
        else:
            enriched_df = self._full_enrichment(raw_df)

        # Add metadata
        enriched_df['enriched_at'] = datetime.now()

        # Save enriched data
        output_file = f"{self.config.enriched_data_path}/{symbol}_{enrichment_level}.parquet"
        enriched_df.to_parquet(output_file, index=False)

        print(f"Batch enrichment complete. Saved to {output_file}")
        print(f"Processed {len(enriched_df)} records")

# Example usage function
def create_hybrid_pipeline():
    """Create and configure hybrid pipeline"""
    config = DataConfig(
        raw_data_path="./data/raw",
        enriched_data_path="./data/enriched",
        enable_realtime=True,
        enrichment_level="standard"
    )

    return HybridDataPipeline(config)

# API endpoint wrapper
async def get_data_for_llm(
    symbol: str,
    lookback_minutes: int = 60,
    enrichment_level: str = "standard",
    pipeline: Optional[HybridDataPipeline] = None
) -> Dict:
    """
    Get data optimized for LLM consumption
    """
    if not pipeline:
        pipeline = create_hybrid_pipeline()

    end_time = datetime.now()
    start_time = end_time - timedelta(minutes=lookback_minutes)

    # Get enriched data
    df = await pipeline.get_enriched_data(
        symbol=symbol,
        start_time=start_time,
        end_time=end_time,
        enrichment_level=enrichment_level
    )

    if df.empty:
        return {
            "status": "no_data",
            "symbol": symbol,
            "message": "No data available for the specified time range"
        }

    # Prepare summary for LLM
    latest = df.iloc[-1]

    summary = {
        "symbol": symbol,
        "timestamp": latest.get('timestamp', datetime.now()).isoformat(),
        "enrichment_level": enrichment_level,
        "current_state": {
            "price": float(latest.get('mid_price', 0)),
            "spread": float(latest.get('spread', 0)),
            "spread_bps": float(latest.get('spread_bps', 0)),
            "volume": int(latest.get('volume', 0)),
        }
    }

    # Add enrichment-specific fields
    if enrichment_level in ["standard", "full"]:
        summary["technical_indicators"] = {
            "rsi": float(latest.get('rsi', 50)),
            "vwap": float(latest.get('vwap', 0)),
            "volatility": float(latest.get('volatility', 0)),
            "volume_imbalance": float(latest.get('volume_imbalance', 0))
        }

    if enrichment_level == "full":
        summary["microstructure"] = {
            "effective_spread": float(latest.get('effective_spread', 0)),
            "realized_spread": float(latest.get('realized_spread', 0)),
            "price_impact": float(latest.get('price_impact', 0)),
            "liquidity_score": float(latest.get('liquidity_score', 0)),
            "toxicity_score": float(latest.get('toxicity_score', 0))
        }
        summary["market_regime"] = {
            "regime": latest.get('market_regime', 'unknown'),
            "trend_strength": float(latest.get('trend_strength', 0))
        }

    # Add time series if needed
    summary["time_series_stats"] = {
        "records": len(df),
        "time_range": {
            "start": df['timestamp'].min().isoformat(),
            "end": df['timestamp'].max().isoformat()
        },
        "price_change": float(df['mid_price'].iloc[-1] - df['mid_price'].iloc[0]),
        "price_change_pct": float((df['mid_price'].iloc[-1] / df['mid_price'].iloc[0] - 1) * 100),
        "avg_spread": float(df['spread'].mean()),
        "total_volume": int(df['volume'].sum())
    }

    return summary

print("Created hybrid_data_pipeline.py")
