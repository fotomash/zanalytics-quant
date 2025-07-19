
"""
ZANFLOW Data Loader Utility
Simple functions to load and work with your parquet files
"""

import pandas as pd
import streamlit as st
from pathlib import Path
import glob
from typing import Dict, List, Optional

class ZanflowDataLoader:
    """Simple data loader for ZANFLOW parquet files"""

    def __init__(self):
        # Get paths from secrets or use defaults
        self.paths = {
            'parquet_dir': Path(st.secrets.get("PARQUET_DATA_DIR", ".")),
            'enriched_dir': Path(st.secrets.get("enriched_data", ".")),
            'raw_dir': Path(st.secrets.get("raw_data_directory", "."))
        }

    @st.cache_data
    def load_latest_file(self, symbol: str = "XAUUSD", timeframe: str = "5min") -> pd.DataFrame:
        """Load the latest parquet file for a symbol/timeframe"""

        # Search pattern
        pattern = f"*{symbol}*{timeframe}*.parquet"

        # Search in all directories
        for dir_name, dir_path in self.paths.items():
            if dir_path.exists():
                files = list(dir_path.glob(pattern))
                if files:
                    # Get most recent file
                    latest_file = max(files, key=lambda x: x.stat().st_mtime)
                    return pd.read_parquet(latest_file)

        return pd.DataFrame()

    @st.cache_data
    def load_tick_data(self, symbol: str = "XAUUSD", limit: int = 10000) -> pd.DataFrame:
        """Load tick data for a symbol"""

        # Try different naming patterns
        patterns = [
            f"*{symbol}*tick*.parquet",
            f"*{symbol}_tick*.parquet",
            f"{symbol}_tick.parquet"
        ]

        for pattern in patterns:
            for dir_name, dir_path in self.paths.items():
                if dir_path.exists():
                    files = list(dir_path.glob(pattern))
                    if files:
                        df = pd.read_parquet(files[0])
                        return df.tail(limit) if len(df) > limit else df

        return pd.DataFrame()

    def list_available_files(self) -> Dict[str, List[str]]:
        """List all available parquet files"""
        available = {}

        for dir_name, dir_path in self.paths.items():
            if dir_path.exists():
                files = list(dir_path.glob("*.parquet"))
                if files:
                    available[dir_name] = [f.name for f in files]

        return available

    def load_enriched_data(self, filename: str) -> pd.DataFrame:
        """Load enriched data file"""
        enriched_path = self.paths['enriched_dir'] / filename

        if enriched_path.exists():
            return pd.read_parquet(enriched_path)

        # Try other directories
        for dir_path in self.paths.values():
            file_path = dir_path / filename
            if file_path.exists():
                return pd.read_parquet(file_path)

        return pd.DataFrame()

# Quick usage functions
def quick_load(symbol: str = "XAUUSD", timeframe: str = "5min") -> pd.DataFrame:
    """Quick load function for scripts"""
    loader = ZanflowDataLoader()
    return loader.load_latest_file(symbol, timeframe)

def load_for_analysis(symbol: str = "XAUUSD") -> Dict[str, pd.DataFrame]:
    """Load multiple timeframes for analysis"""
    loader = ZanflowDataLoader()

    timeframes = ['tick', '1min', '5min', '15min', '1H', '4H', '1D']
    data = {}

    for tf in timeframes:
        df = loader.load_latest_file(symbol, tf)
        if not df.empty:
            data[tf] = df
            print(f"Loaded {tf}: {len(df)} rows")

    return data

# Example usage in Streamlit
def demo_usage():
    """Demo of how to use the data loader"""
    st.title("ZANFLOW Data Loader Demo")

    loader = ZanflowDataLoader()

    # Show available files
    st.subheader("Available Files")
    files = loader.list_available_files()
    for dir_name, file_list in files.items():
        st.write(f"**{dir_name}**: {len(file_list)} files")
        with st.expander(f"View {dir_name} files"):
            for f in file_list[:10]:  # Show first 10
                st.write(f"- {f}")

    # Load specific file
    symbol = st.selectbox("Symbol", ["XAUUSD", "EURUSD", "BTCUSD"])
    timeframe = st.selectbox("Timeframe", ["tick", "1min", "5min", "15min", "1H"])

    if st.button("Load Data"):
        df = loader.load_latest_file(symbol, timeframe)
        if not df.empty:
            st.success(f"Loaded {len(df)} rows")
            st.dataframe(df.head())
        else:
            st.warning("No data found")

if __name__ == "__main__":
    demo_usage()
