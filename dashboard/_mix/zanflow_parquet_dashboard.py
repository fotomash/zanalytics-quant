
"""
ZANFLOW Parquet Data Integration Dashboard
Reads directly from your configured parquet directories
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
from pathlib import Path
from datetime import datetime, timedelta
import pyarrow.parquet as pq
import glob
import os

# Page config
st.set_page_config(
    page_title="ZANFLOW Parquet Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

class ParquetDataManager:
    """Manages parquet file operations from configured directories"""

    def __init__(self):
        # Get paths from Streamlit secrets
        self.paths = {
            'parquet': st.secrets.get("PARQUET_DATA_DIR", "/Users/tom/Documents/_trade/_exports/_tick/parquet/"),
            'enriched': st.secrets.get("enriched_data", "/Users/tom/Documents/_trade/_exports/_tick/parquet"),
            'raw': st.secrets.get("raw_data_directory", "/Users/tom/Documents/_trade/_exports/_tick/_raw"),
            'json': st.secrets.get("JSONdir", "/Users/tom/Documents/_trade/_exports/_tick/midas_analysis"),
            'bars': st.secrets.get("bar_data_directory", "/Users/tom/Documents/_trade/_exports/_tick/_bars")
        }

        # Validate paths
        self.valid_paths = {}
        for name, path in self.paths.items():
            if Path(path).exists():
                self.valid_paths[name] = Path(path)

    def scan_parquet_files(self) -> dict:
        """Scan all directories for parquet files"""
        all_files = {}

        for name, path in self.valid_paths.items():
            # Find all parquet files in directory
            pattern = str(path / "**/*.parquet")
            files = glob.glob(pattern, recursive=True)

            if files:
                all_files[name] = []
                for file in files:
                    file_path = Path(file)
                    file_info = {
                        'path': file_path,
                        'name': file_path.name,
                        'size_mb': file_path.stat().st_size / 1024 / 1024,
                        'modified': datetime.fromtimestamp(file_path.stat().st_mtime),
                        'symbol': self._extract_symbol(file_path.name),
                        'timeframe': self._extract_timeframe(file_path.name)
                    }
                    all_files[name].append(file_info)

        return all_files

    def _extract_symbol(self, filename: str) -> str:
        """Extract symbol from filename"""
        # Common patterns: XAUUSD_5min.parquet, EURUSD_tick.parquet
        parts = filename.replace('.parquet', '').split('_')
        if parts:
            return parts[0]
        return 'Unknown'

    def _extract_timeframe(self, filename: str) -> str:
        """Extract timeframe from filename"""
        if 'tick' in filename.lower():
            return 'tick'
        elif '1min' in filename:
            return '1min'
        elif '5min' in filename:
            return '5min'
        elif '15min' in filename:
            return '15min'
        elif '1h' in filename or '60min' in filename:
            return '1H'
        elif '4h' in filename:
            return '4H'
        elif '1d' in filename or 'daily' in filename:
            return '1D'
        return 'unknown'

    def load_parquet_file(self, file_path: Path, sample_size: int = None) -> pd.DataFrame:
        """Load parquet file with optional sampling"""
        try:
            if sample_size:
                # Read only specific number of rows
                return pd.read_parquet(file_path).tail(sample_size)
            else:
                return pd.read_parquet(file_path)
        except Exception as e:
            st.error(f"Error loading {file_path.name}: {str(e)}")
            return pd.DataFrame()

    def get_parquet_metadata(self, file_path: Path) -> dict:
        """Get metadata from parquet file without loading all data"""
        try:
            parquet_file = pq.ParquetFile(file_path)
            metadata = parquet_file.metadata
            schema = parquet_file.schema

            return {
                'num_rows': metadata.num_rows,
                'num_columns': len(schema),
                'columns': [str(field.name) for field in schema],
                'size_mb': file_path.stat().st_size / 1024 / 1024,
                'created': metadata.created_by if hasattr(metadata, 'created_by') else 'Unknown'
            }
        except Exception as e:
            return {'error': str(e)}

    def load_multiple_timeframes(self, symbol: str) -> dict:
        """Load multiple timeframes for a symbol"""
        timeframes = {}

        for name, files in self.scan_parquet_files().items():
            for file_info in files:
                if file_info['symbol'] == symbol:
                    tf = file_info['timeframe']
                    if tf not in timeframes:
                        df = self.load_parquet_file(file_info['path'], sample_size=5000)
                        if not df.empty:
                            timeframes[tf] = df

        return timeframes

class UnifiedAnalyzer:
    """Unified analysis engine for parquet data"""

    def __init__(self):
        self.data_manager = ParquetDataManager()

    def analyze_microstructure(self, df: pd.DataFrame) -> dict:
        """Run microstructure analysis on data"""
        results = {
            'data_quality': self._check_data_quality(df),
            'price_analysis': self._analyze_price_action(df),
            'volume_analysis': self._analyze_volume(df),
            'liquidity_analysis': self._analyze_liquidity(df)
        }

        return results

    def _check_data_quality(self, df: pd.DataFrame) -> dict:
        """Check data quality and completeness"""
        return {
            'rows': len(df),
            'columns': list(df.columns),
            'missing_values': df.isnull().sum().to_dict(),
            'date_range': f"{df.index.min()} to {df.index.max()}" if not df.empty else "N/A"
        }

    def _analyze_price_action(self, df: pd.DataFrame) -> dict:
        """Analyze price action patterns"""
        if 'close' not in df.columns and 'bid' in df.columns:
            df['close'] = (df['bid'] + df['ask']) / 2

        if 'close' in df.columns:
            return {
                'current_price': df['close'].iloc[-1],
                'high': df['close'].max(),
                'low': df['close'].min(),
                'volatility': df['close'].std(),
                'trend': 'UP' if df['close'].iloc[-1] > df['close'].iloc[0] else 'DOWN'
            }
        return {}

    def _analyze_volume(self, df: pd.DataFrame) -> dict:
        """Analyze volume patterns"""
        volume_cols = [col for col in df.columns if 'volume' in col.lower()]

        if volume_cols:
            vol_col = volume_cols[0]
            return {
                'total_volume': df[vol_col].sum(),
                'avg_volume': df[vol_col].mean(),
                'volume_spike': df[vol_col].max() / df[vol_col].mean() if df[vol_col].mean() > 0 else 0
            }
        return {}

    def _analyze_liquidity(self, df: pd.DataFrame) -> dict:
        """Analyze liquidity and spread"""
        if 'bid' in df.columns and 'ask' in df.columns:
            df['spread'] = df['ask'] - df['bid']
            return {
                'avg_spread': df['spread'].mean(),
                'max_spread': df['spread'].max(),
                'min_spread': df['spread'].min(),
                'spread_volatility': df['spread'].std()
            }
        return {}

def main():
    st.title("📊 ZANFLOW Parquet Data Dashboard")
    st.markdown("*Direct integration with your local parquet files*")

    # Initialize components
    data_manager = ParquetDataManager()
    analyzer = UnifiedAnalyzer()

    # Sidebar
    with st.sidebar:
        st.header("📁 Data Configuration")

        # Show configured paths
        st.subheader("Configured Paths")
        for name, path in data_manager.valid_paths.items():
            st.success(f"✅ {name}: .../{path.name}")

        # Scan for files
        if st.button("🔍 Scan for Parquet Files"):
            st.session_state['scanned_files'] = data_manager.scan_parquet_files()

        # File selection
        if 'scanned_files' in st.session_state:
            all_files = st.session_state['scanned_files']

            # Create file selector
            st.subheader("📄 Select File")

            # Group files by directory
            for directory, files in all_files.items():
                if files:
                    st.markdown(f"**{directory.upper()}** ({len(files)} files)")

                    # Show files in this directory
                    for file_info in files[:10]:  # Show first 10
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            if st.button(
                                f"{file_info['symbol']} - {file_info['timeframe']}",
                                key=f"file_{file_info['path']}"
                            ):
                                st.session_state['selected_file'] = file_info
                        with col2:
                            st.caption(f"{file_info['size_mb']:.1f}MB")

        # Analysis options
        st.subheader("⚙️ Analysis Options")
        load_limit = st.number_input("Max rows to load", 1000, 1000000, 10000)
        enable_multi_tf = st.checkbox("Load multiple timeframes", value=False)

    # Main content area
    if 'selected_file' in st.session_state:
        file_info = st.session_state['selected_file']

        st.header(f"Analysis: {file_info['symbol']} - {file_info['timeframe']}")

        # File metadata
        with st.expander("📋 File Information", expanded=False):
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("File Size", f"{file_info['size_mb']:.2f} MB")
            with col2:
                st.metric("Last Modified", file_info['modified'].strftime("%Y-%m-%d %H:%M"))
            with col3:
                # Get detailed metadata
                metadata = data_manager.get_parquet_metadata(file_info['path'])
                if 'num_rows' in metadata:
                    st.metric("Total Rows", f"{metadata['num_rows']:,}")

        # Load data
        with st.spinner(f"Loading {file_info['name']}..."):
            df = data_manager.load_parquet_file(file_info['path'], sample_size=load_limit)

        if not df.empty:
            # Data preview
            st.subheader("📈 Data Preview")

            # Show basic stats
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Rows Loaded", f"{len(df):,}")
            with col2:
                st.metric("Columns", len(df.columns))
            with col3:
                if 'timestamp' in df.columns:
                    st.metric("Start", df['timestamp'].iloc[0])
            with col4:
                if 'timestamp' in df.columns:
                    st.metric("End", df['timestamp'].iloc[-1])

            # Show data sample
            with st.expander("🔍 View Data Sample", expanded=True):
                st.dataframe(df.head(100), use_container_width=True)

            # Column information
            with st.expander("📊 Column Information"):
                col_info = pd.DataFrame({
                    'Column': df.columns,
                    'Type': df.dtypes,
                    'Non-Null': df.count(),
                    'Unique': df.nunique()
                })
                st.dataframe(col_info, use_container_width=True)

            # Run analysis
            st.subheader("🔬 Microstructure Analysis")

            if st.button("🚀 Run Analysis", type="primary"):
                with st.spinner("Analyzing data..."):
                    analysis_results = analyzer.analyze_microstructure(df)

                    # Display results in tabs
                    tab1, tab2, tab3, tab4 = st.tabs(["Price", "Volume", "Liquidity", "Quality"])

                    with tab1:
                        if analysis_results['price_analysis']:
                            price_data = analysis_results['price_analysis']
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.metric("Current Price", f"{price_data.get('current_price', 0):.5f}")
                            with col2:
                                st.metric("Volatility", f"{price_data.get('volatility', 0):.5f}")
                            with col3:
                                st.metric("Trend", price_data.get('trend', 'N/A'))

                            # Price chart
                            if 'close' in df.columns or 'bid' in df.columns:
                                fig = go.Figure()

                                if 'close' in df.columns:
                                    y_data = df['close']
                                else:
                                    y_data = (df['bid'] + df['ask']) / 2

                                fig.add_trace(go.Scatter(
                                    x=df.index[:1000],  # Limit points for performance
                                    y=y_data[:1000],
                                    mode='lines',
                                    name='Price'
                                ))

                                fig.update_layout(
                                    title='Price Movement',
                                    xaxis_title='Index',
                                    yaxis_title='Price',
                                    height=400
                                )

                                st.plotly_chart(fig, use_container_width=True)

                    with tab2:
                        if analysis_results['volume_analysis']:
                            vol_data = analysis_results['volume_analysis']
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.metric("Total Volume", f"{vol_data.get('total_volume', 0):,.0f}")
                            with col2:
                                st.metric("Avg Volume", f"{vol_data.get('avg_volume', 0):,.2f}")
                            with col3:
                                st.metric("Max Spike", f"{vol_data.get('volume_spike', 0):.1f}x")

                    with tab3:
                        if analysis_results['liquidity_analysis']:
                            liq_data = analysis_results['liquidity_analysis']
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.metric("Avg Spread", f"{liq_data.get('avg_spread', 0):.5f}")
                            with col2:
                                st.metric("Max Spread", f"{liq_data.get('max_spread', 0):.5f}")
                            with col3:
                                st.metric("Spread Vol", f"{liq_data.get('spread_volatility', 0):.5f}")

                    with tab4:
                        quality = analysis_results['data_quality']
                        st.metric("Total Rows", quality['rows'])
                        st.markdown("**Available Columns:**")
                        st.code(', '.join(quality['columns']))
                        if quality['missing_values']:
                            st.markdown("**Missing Values:**")
                            missing_df = pd.DataFrame(
                                list(quality['missing_values'].items()),
                                columns=['Column', 'Missing Count']
                            )
                            st.dataframe(missing_df[missing_df['Missing Count'] > 0])

            # Multi-timeframe analysis
            if enable_multi_tf:
                st.subheader("📊 Multi-Timeframe Analysis")

                if st.button("Load All Timeframes"):
                    with st.spinner(f"Loading all timeframes for {file_info['symbol']}..."):
                        timeframes = data_manager.load_multiple_timeframes(file_info['symbol'])

                        if timeframes:
                            st.success(f"Loaded {len(timeframes)} timeframes")

                            # Show summary for each timeframe
                            for tf, tf_df in timeframes.items():
                                with st.expander(f"⏰ {tf} - {len(tf_df)} rows"):
                                    if 'close' in tf_df.columns or 'bid' in tf_df.columns:
                                        col1, col2, col3 = st.columns(3)

                                        if 'close' in tf_df.columns:
                                            price_col = 'close'
                                        else:
                                            price_col = 'mid'
                                            tf_df['mid'] = (tf_df['bid'] + tf_df['ask']) / 2

                                        with col1:
                                            st.metric("Start Price", f"{tf_df[price_col].iloc[0]:.5f}")
                                        with col2:
                                            st.metric("End Price", f"{tf_df[price_col].iloc[-1]:.5f}")
                                        with col3:
                                            change = ((tf_df[price_col].iloc[-1] / tf_df[price_col].iloc[0]) - 1) * 100
                                            st.metric("Change", f"{change:.2f}%")

    else:
        # Welcome screen
        st.info("👈 Click 'Scan for Parquet Files' in the sidebar to start")

        # Show quick stats if we have valid paths
        if data_manager.valid_paths:
            st.subheader("📊 Quick Overview")

            total_files = 0
            total_size = 0

            for name, path in data_manager.valid_paths.items():
                files = list(path.glob("*.parquet"))
                if files:
                    file_count = len(files)
                    size_mb = sum(f.stat().st_size for f in files) / 1024 / 1024
                    total_files += file_count
                    total_size += size_mb

                    st.metric(f"{name.upper()} Directory", f"{file_count} files ({size_mb:.1f} MB)")

            if total_files > 0:
                st.success(f"Total: {total_files} parquet files ({total_size:.1f} MB)")

if __name__ == "__main__":
    main()
