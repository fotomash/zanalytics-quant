#!/usr/bin/env python3
"""
Zanalytics - Multi-Timeframe Analysis Dashboard

A dedicated tool for comparing metrics across multiple timeframes for a selected symbol.
"""
import streamlit as st
import pandas as pd
import numpy as np
import os
import glob
from pathlib import Path
import warnings
import re
from typing import Dict, List, Optional, Any
import plotly.graph_objects as go
import plotly.express as px

# Suppress warnings for a cleaner output
warnings.filterwarnings('ignore')


class MultiTimeframeDashboard:
    def __init__(self):
        """
        Initializes the dashboard, loading configuration from Streamlit secrets.
        """
        try:
            # Load data directory from secrets.toml
            data_directory = st.secrets["data_directory"]
        except (FileNotFoundError, KeyError):
            # Fallback to a default directory if secrets.toml or the key is missing
            data_directory = "./data"

        self.data_dir = Path(data_directory)
        self.supported_pairs = ["XAUUSD", "BTCUSD", "EURUSD", "GBPUSD", "USDJPY", "ETHUSD", "USDCAD", "AUDUSD",
                                "NZDUSD", "DXYCAS"]
        self.timeframes = ["1min", "5min", "15min", "30min", "1H", "4H", "1D", "1W", "5T"]

        # --- Session State Initialization ---
        if 'chart_theme' not in st.session_state:
            st.session_state.chart_theme = 'plotly_dark'
        if 'lookback_bars' not in st.session_state:
            st.session_state.lookback_bars = 500
        if 'lookback_ticks' not in st.session_state:
            st.session_state.lookback_ticks = 1000
        if 'selected_symbol' not in st.session_state:
            st.session_state.selected_symbol = None

    def run(self):
        st.set_page_config(page_title="Zanalytics - Multi-Timeframe", page_icon="⏱️", layout="wide",
                           initial_sidebar_state="expanded")

        import base64
        def get_image_as_base64(path):
            try:
                with open(path, "rb") as image_file:
                    return base64.b64encode(image_file.read()).decode()
            except FileNotFoundError:
                st.warning(f"Background image not found at '{path}'")
                return None

        img_base64 = get_image_as_base64("theme/image_af247b.jpg")
        if img_base64:
            st.markdown(f"""
            <style>
            [data-testid="stAppViewContainer"] > .main {{
                background: linear-gradient(rgba(0,0,0,0.85), rgba(0,0,0,0.85)), url(data:image/jpeg;base64,{img_base64}) !important;
                background-size: cover !important;
                background-position: center !important;
                background-repeat: no-repeat !important;
                background-attachment: fixed !important;
                background-color: transparent !important;
            }}
            body, .block-container {{
                background: none !important;
                background-color: transparent !important;
            }}
            </style>
            """, unsafe_allow_html=True)

        st.markdown("""
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            </style>
            """, unsafe_allow_html=True)

        if not self.data_dir.exists():
            st.error(f"Data directory not found at: `{self.data_dir}`")
            st.info(
                "Please create this directory or configure the correct path in your `.streamlit/secrets.toml` file.")
            st.code('data_directory = "/path/to/your/data"')
            return

        with st.spinner("🛰️ Scanning all data sources..."):
            data_sources = self.scan_all_data_sources()

        self.create_sidebar()
        self.display_analysis_page(data_sources)

    def create_sidebar(self):
        """Create the sidebar for display settings."""
        st.sidebar.title("Zanalytics")
        st.sidebar.markdown("---")
        st.sidebar.markdown("### 🎨 Display Settings")
        st.session_state.chart_theme = st.sidebar.selectbox(
            "Chart Theme",
            ["plotly_dark", "plotly_white", "ggplot2", "seaborn"],
            key="theme_select"
        )
        st.session_state.lookback_ticks = st.sidebar.slider(
            "Tick Lookback Period", 100, 10000, st.session_state.lookback_ticks
        )
        st.session_state.lookback_bars = st.sidebar.slider(
            "Bar Lookback Period", 50, 2000, st.session_state.lookback_bars
        )

    def display_analysis_page(self, data_sources):
        st.markdown("## ⏱️ Multi-Timeframe Analysis")

        available_pairs = list(data_sources.keys())
        if not available_pairs:
            st.info("No data found to analyze. Please check your data directory.")
            return

        # --- Main Panel Controls ---
        col1, col2 = st.columns(2)
        with col1:
            selected_symbol = st.selectbox("Select Trading Pair", available_pairs)

        if not selected_symbol:
            return

        available_tfs = list(data_sources.get(selected_symbol, {}).keys())
        if not available_tfs:
            st.warning(f"No timeframes found for {selected_symbol}.")
            return

        with col2:
            selected_tfs = st.multiselect(
                "Select Timeframe",
                available_tfs,
                default=available_tfs[:3] if len(available_tfs) >= 3 else available_tfs
            )

        if not selected_tfs:
            st.info("Please select at least one timeframe to compare.")
            return

        # --- Dynamic Metric Selection ---
        all_columns = self.get_all_available_columns(data_sources, selected_symbol, selected_tfs)
        default_metrics = [col for col in ['Timeframe', 'rsi_14', 'atr_14', 'volume'] if col in all_columns]

        selected_metrics = st.multiselect(
            "Select Metrics to Display",
            all_columns,
            default=default_metrics
        )

        # Cross-Timeframe Metrics
        st.markdown("#### 📊 Cross-Timeframe Metrics")
        metrics_data = []
        for tf in selected_tfs:
            file_path = data_sources.get(selected_symbol, {}).get(tf)
            if file_path:
                df = self.load_comprehensive_data(file_path)
                if df is not None and not df.empty:
                    metrics = self.calculate_metrics(df, all_columns)
                    metrics['Timeframe'] = tf
                    metrics_data.append(metrics)

        if metrics_data and selected_metrics:
            metrics_df = pd.DataFrame(metrics_data)
            display_cols = ['Timeframe'] + [m for m in selected_metrics if m != 'Timeframe']
            st.dataframe(metrics_df[display_cols], use_container_width=True, hide_index=True)

            self.create_metrics_chart(metrics_df, selected_metrics)

    def create_metrics_chart(self, metrics_df: pd.DataFrame, selected_metrics: List[str]):
        """Creates a Plotly chart to visualize the selected metrics across timeframes."""
        st.markdown("#### 📈 Metrics Comparison Chart")

        fig = go.Figure()

        tf_order = {tf: i for i, tf in enumerate(self.timeframes)}
        metrics_df['tf_order'] = metrics_df['Timeframe'].map(tf_order)
        metrics_df.sort_values('tf_order', inplace=True)

        for metric in selected_metrics:
            if metric == 'Timeframe':
                continue

            y_values = pd.to_numeric(metrics_df[metric], errors='coerce')

            if not y_values.isna().all():
                fig.add_trace(go.Scatter(
                    x=metrics_df['Timeframe'],
                    y=y_values,
                    mode='lines+markers',
                    name=metric
                ))

        fig.update_layout(
            title="Selected Metrics Across Timeframes",
            xaxis_title="Timeframe",
            yaxis_title="Value",
            template=st.session_state.get('chart_theme', 'plotly_dark'),
            height=400
        )
        st.plotly_chart(fig, use_container_width=True)

    def get_all_available_columns(self, data_sources, symbol, timeframes) -> List[str]:
        """Gets a unique list of all columns available across the selected dataframes."""
        all_cols = set()
        for tf in timeframes:
            file_path = data_sources.get(symbol, {}).get(tf)
            if file_path:
                try:
                    df_cols = pd.read_csv(file_path, nrows=0).columns.str.lower()
                    all_cols.update(df_cols)
                except Exception:
                    continue

        standardized_cols = set()
        rename_map = {'o': 'open', 'h': 'high', 'l': 'low', 'c': 'close', 'v': 'volume'}
        for col in all_cols:
            standardized_cols.add(rename_map.get(col, col))

        return sorted(list(standardized_cols))

    def calculate_metrics(self, df: pd.DataFrame, columns_to_extract: List[str]) -> Dict[str, Any]:
        """Calculates key metrics for a given dataframe for all specified columns."""
        metrics = {}
        if df is None or df.empty:
            return metrics

        try:
            last_row = df.iloc[-1]
            for col in columns_to_extract:
                if col in df.columns:
                    value = last_row[col]
                    if isinstance(value, pd.Series):
                        value = value.iloc[0]
                    if pd.notna(value):
                        val = value
                        if isinstance(val, (int, float)):
                            if abs(val) > 1000:
                                metrics[col] = f"{val:,.0f}"
                            else:
                                metrics[col] = f"{val:.4f}"
                        else:
                            metrics[col] = val
                    else:
                        metrics[col] = np.nan
                else:
                    metrics[col] = np.nan
        except Exception:
            # Ensure the method always returns a dictionary even if something goes wrong
            for col in columns_to_extract:
                metrics[col] = np.nan

        return metrics
    def scan_all_data_sources(self) -> Dict[str, Dict[str, str]]:
        """Scans for data files in the configured directory and its subdirectories."""
        data_sources = {}
        all_files = glob.glob(os.path.join(self.data_dir, "**", "*.*"), recursive=True)

        for f_path in all_files:
            parent_dir_name = Path(f_path).parent.name

            found_pair = None
            if parent_dir_name.upper() in self.supported_pairs:
                found_pair = parent_dir_name.upper()
            else:
                for pair in self.supported_pairs:
                    if pair in Path(f_path).name:
                        found_pair = pair
                        break

            if found_pair and f_path.endswith(('.csv', '.parquet')):
                for tf in self.timeframes:
                    if tf in Path(f_path).name:
                        if found_pair not in data_sources:
                            data_sources[found_pair] = {}
                        data_sources[found_pair][tf] = f_path
                        break
        return data_sources

    def load_comprehensive_data(self, file_path: str, max_records: Optional[int] = None) -> Optional[pd.DataFrame]:
        """Loads and enriches data, ensuring required columns are present."""
        try:
            df = pd.read_parquet(file_path) if file_path.endswith('.parquet') else pd.read_csv(file_path, sep=None,
                                                                                               engine='python')
            df.columns = [col.lower().strip() for col in df.columns]
            for col in ['timestamp', 'datetime', 'date']:
                if col in df.columns:
                    df.set_index(pd.to_datetime(df[col]), inplace=True)
                    df.drop(columns=[col], inplace=True)
                    break
            if not isinstance(df.index, pd.DatetimeIndex):
                df.index = pd.to_datetime(df.index)
            df.rename(columns={'o': 'open', 'h': 'high', 'l': 'low', 'c': 'close', 'v': 'volume'}, inplace=True)

            # Enrich with RSI
            if 'rsi_14' not in df.columns and 'close' in df.columns and len(df) >= 15:
                delta = df['close'].diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                rs = gain / loss
                df['rsi_14'] = 100 - (100 / (1 + rs))

            # Enrich with ATR
            if 'atr_14' not in df.columns and all(c in df.columns for c in ['high', 'low', 'close']) and len(df) >= 14:
                high_low = df['high'] - df['low']
                high_close = abs(df['high'] - df['close'].shift())
                low_close = abs(df['low'] - df['close'].shift())
                tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
                df['atr_14'] = tr.rolling(14).mean()

            if max_records: df = df.tail(max_records)
            return df
        except Exception:
            return None


if __name__ == "__main__":
    dashboard = MultiTimeframeDashboard()
    dashboard.run()
