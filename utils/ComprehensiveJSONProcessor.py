import streamlit as st
import pandas as pd
import numpy as np
import json
import ast
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path
import os
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple

# ncOS session state
session_state = {
    "loaded_files": {},
    "active_symbol": None,
    "data_cache": {},
    "analysis_cache": {}
}

class ComprehensiveJSONProcessor:
    """Process comprehensive JSON files with proper error handling"""

    @staticmethod
    def _safe_array(value: str) -> Optional[list]:
        """Safely parse numeric arrays from string values."""
        try:
            parsed = json.loads(value.replace('nan', 'null'))
        except json.JSONDecodeError:
            try:
                parsed = ast.literal_eval(value)
            except (ValueError, SyntaxError):
                return None
        if isinstance(parsed, list):
            return [np.nan if v is None else v for v in parsed]
        return None
    
    @staticmethod
    def scan_symbol_files(symbol: str) -> Dict[str, Path]:
        """Scan all JSON files for a symbol with safe parsing"""
        files = {}
        symbol_dir = Path(f"./data/{symbol}")
        
        if symbol_dir.exists():
            # Comprehensive file
            comp_file = symbol_dir / f"{symbol}_comprehensive.json"
            if comp_file.exists():
                files['comprehensive'] = comp_file
            
            # Scan for other JSON files with safe parsing
            for json_file in symbol_dir.glob("*.json"):
                filename = json_file.stem
                
                # Skip if already added
                if filename == f"{symbol}_comprehensive":
                    continue
                
                # Safe parsing for M1 files
                if '_M1_' in filename:
                    try:
                        parts = filename.split('_M1_')
                        if len(parts) > 1:
                            processing_type = parts[1]
                            files[f'M1_{processing_type}'] = json_file
                    except:
                        # Fallback: use full filename
                        files[filename] = json_file
                # Summary files
                elif filename.startswith('summary_'):
                    files[filename] = json_file
                # Processing journal
                elif filename == 'processing_journal':
                    files['processing_journal'] = json_file
                # Other JSON files
                else:
                    files[filename] = json_file
        
        return files
    
    @staticmethod
    def extract_data_from_comprehensive(json_data: Dict[str, Any]) -> Dict[str, pd.DataFrame]:
        """Extract all data sources from comprehensive JSON"""
        dataframes = {}
        
        # Process each source file in the comprehensive JSON
        for source_file, source_data in json_data.items():
            if isinstance(source_data, dict) and 'analysis_timestamp' in source_data:
                try:
                    # Create base dataframe from indicators if available
                    if 'indicators' in source_data:
                        indicators = source_data['indicators']
                        
                        # Find the length of data
                        data_length = 0
                        for key, value in indicators.items():
                            if isinstance(value, str) and value.startswith('['):
                                # Parse the string representation of array
                                try:
                                    arr = ComprehensiveJSONProcessor._safe_array(value)
                                    if arr is not None:
                                        data_length = len(arr)
                                        break
                                except Exception:
                                    pass
                        
                        if data_length > 0:
                            # Create dataframe with all indicators
                            df_data = {}
                            
                            # Add basic columns if available
                            if 'basic_stats' in source_data:
                                stats = source_data['basic_stats']
                                if 'start_time' in stats and 'end_time' in stats:
                                    # Create timestamp range
                                    try:
                                        start = pd.to_datetime(stats['start_time'])
                                        end = pd.to_datetime(stats['end_time'])
                                        timestamps = pd.date_range(start=start, end=end, periods=data_length)
                                        df_data['timestamp'] = timestamps
                                    except:
                                        df_data['timestamp'] = range(data_length)
                            
                            # Parse all indicators
                            for key, value in indicators.items():
                                if isinstance(value, str) and value.startswith('['):
                                try:
                                    arr = ComprehensiveJSONProcessor._safe_array(value)
                                    if arr is not None and len(arr) == data_length:
                                        df_data[key] = arr
                                except Exception:
                                    pass
                            
                            if df_data:
                                df = pd.DataFrame(df_data)
                                
                                # Add metadata
                                df.attrs['source'] = source_file
                                df.attrs['basic_stats'] = source_data.get('basic_stats', {})
                                df.attrs['currency_pair'] = source_data.get('currency_pair', 'Unknown')
                                df.attrs['timeframe'] = source_data.get('timeframe', 'Unknown')
                                
                                dataframes[source_file] = df
                    
                    # Extract SMC analysis as separate dataframe
                    if 'smc_analysis' in source_data:
                        smc_data = source_data['smc_analysis']
                        
                        # Market structure
                        if 'market_structure' in smc_data:
                            ms = smc_data['market_structure']
                            
                            # Swing highs
                            if 'swing_highs' in ms and ms['swing_highs']:
                                swing_highs_df = pd.DataFrame(ms['swing_highs'])
                                swing_highs_df['type'] = 'swing_high'
                                dataframes['smc_swing_highs'] = swing_highs_df
                            
                            # Swing lows
                            if 'swing_lows' in ms and ms['swing_lows']:
                                swing_lows_df = pd.DataFrame(ms['swing_lows'])
                                swing_lows_df['type'] = 'swing_low'
                                dataframes['smc_swing_lows'] = swing_lows_df
                        
                        # Order blocks
                        if 'order_blocks' in smc_data:
                            ob_data = smc_data['order_blocks']
                            if 'bullish' in ob_data and ob_data['bullish']:
                                bullish_ob_df = pd.DataFrame(ob_data['bullish'])
                                bullish_ob_df['type'] = 'bullish_ob'
                                dataframes['smc_bullish_ob'] = bullish_ob_df
                            if 'bearish' in ob_data and ob_data['bearish']:
                                bearish_ob_df = pd.DataFrame(ob_data['bearish'])
                                bearish_ob_df['type'] = 'bearish_ob'
                                dataframes['smc_bearish_ob'] = bearish_ob_df
                    
                    # Extract harmonic patterns
                    if 'harmonic_patterns' in source_data and source_data['harmonic_patterns']:
                        patterns_df = pd.DataFrame(source_data['harmonic_patterns'])
                        dataframes['harmonic_patterns'] = patterns_df
                
                except Exception as e:
                    print(f"Error processing {source_file}: {e}")
        
        return dataframes
    
    @staticmethod
    def create_comprehensive_visualization(dataframes: Dict[str, pd.DataFrame], symbol: str) -> go.Figure:
        """Create comprehensive multi-panel visualization from extracted data"""
        
        # Find main data source (largest dataframe with indicators)
        main_df = None
        main_source = None
        
        for source, df in dataframes.items():
            if 'timestamp' in df.columns and len(df) > 100:
                if main_df is None or len(df) > len(main_df):
                    main_df = df
                    main_source = source
        
        if main_df is None:
            return go.Figure().add_annotation(text="No time series data found", showarrow=False)
        
        # Calculate subplot configuration
        num_rows = 5  # Price, Volume, RSI, MACD, Custom
        row_heights = [0.4, 0.15, 0.15, 0.15, 0.15]
        
        fig = make_subplots(
            rows=num_rows,
            cols=1,
            shared_xaxes=True,
            vertical_spacing=0.02,
            row_heights=row_heights,
            subplot_titles=[
                f"{symbol} Price Action",
                "Volume Profile",
                "RSI Analysis",
                "MACD",
                "Advanced Indicators"
            ]
        )
        
        # 1. Price Chart with multiple overlays
        # Check for price columns
        if 'close' in main_df.columns:
            price_col = 'close'
        elif any(col.endswith('close') for col in main_df.columns):
            price_col = [col for col in main_df.columns if col.endswith('close')][0]
        else:
            # Use first numeric column as proxy
            numeric_cols = main_df.select_dtypes(include=[np.number]).columns
            price_col = numeric_cols[0] if len(numeric_cols) > 0 else None
        
        if price_col:
            # Main price line
            fig.add_trace(go.Scatter(
                x=main_df['timestamp'] if 'timestamp' in main_df.columns else main_df.index,
                y=main_df[price_col],
                name='Price',
                line=dict(color='blue', width=2)
            ), row=1, col=1)
            
            # Add moving averages
            ma_colors = {'SMA_20': 'orange', 'SMA_50': 'green', 'SMA_200': 'red',
                        'EMA_20': 'purple', 'EMA_50': 'brown', 'EMA_200': 'pink'}
            
            for ma, color in ma_colors.items():
                if ma in main_df.columns:
                    fig.add_trace(go.Scatter(
                        x=main_df['timestamp'] if 'timestamp' in main_df.columns else main_df.index,
                        y=main_df[ma],
                        name=ma,
                        line=dict(color=color, width=1),
                        opacity=0.7
                    ), row=1, col=1)
            
            # Add Bollinger Bands
            if all(col in main_df.columns for col in ['BB_UPPER_20', 'BB_MIDDLE_20', 'BB_LOWER_20']):
                fig.add_trace(go.Scatter(
                    x=main_df['timestamp'] if 'timestamp' in main_df.columns else main_df.index,
                    y=main_df['BB_UPPER_20'],
                    name='BB Upper',
                    line=dict(color='gray', width=1, dash='dash'),
                    showlegend=False
                ), row=1, col=1)
                
                fig.add_trace(go.Scatter(
                    x=main_df['timestamp'] if 'timestamp' in main_df.columns else main_df.index,
                    y=main_df['BB_LOWER_20'],
                    name='BB Lower',
                    line=dict(color='gray', width=1, dash='dash'),
                    fill='tonexty',
                    fillcolor='rgba(128,128,128,0.1)',
                    showlegend=False
                ), row=1, col=1)
        
        # Add swing points if available
        if 'smc_swing_highs' in dataframes:
            swing_highs = dataframes['smc_swing_highs']
            if 'index' in swing_highs.columns and 'price' in swing_highs.columns:
                # Map indices to timestamps
                indices = swing_highs['index'].values
                if 'timestamp' in main_df.columns:
                    valid_indices = indices[indices < len(main_df)]
                    timestamps = main_df.iloc[valid_indices]['timestamp']
                    prices = swing_highs[swing_highs['index'].isin(valid_indices)]['price']
                    
                    fig.add_trace(go.Scatter(
                        x=timestamps,
                        y=prices,
                        mode='markers',
                        marker=dict(symbol='triangle-down', size=10, color='red'),
                        name='Swing Highs'
                    ), row=1, col=1)
        
        if 'smc_swing_lows' in dataframes:
            swing_lows = dataframes['smc_swing_lows']
            if 'index' in swing_lows.columns and 'price' in swing_lows.columns:
                indices = swing_lows['index'].values
                if 'timestamp' in main_df.columns:
                    valid_indices = indices[indices < len(main_df)]
                    timestamps = main_df.iloc[valid_indices]['timestamp']
                    prices = swing_lows[swing_lows['index'].isin(valid_indices)]['price']
                    
                    fig.add_trace(go.Scatter(
                        x=timestamps,
                        y=prices,
                        mode='markers',
                        marker=dict(symbol='triangle-up', size=10, color='green'),
                        name='Swing Lows'
                    ), row=1, col=1)
        
        # 2. Volume (if available)
        volume_cols = [col for col in main_df.columns if 'volume' in col.lower() and 'ma' not in col.lower()]
        if volume_cols:
            fig.add_trace(go.Bar(
                x=main_df['timestamp'] if 'timestamp' in main_df.columns else main_df.index,
                y=main_df[volume_cols[0]],
                name='Volume',
                marker_color='lightblue'
            ), row=2, col=1)
        
        # 3. RSI
        rsi_cols = [col for col in main_df.columns if col.startswith('RSI_')]
        if rsi_cols:
            for rsi_col in rsi_cols[:2]:  # Max 2 RSI lines
                fig.add_trace(go.Scatter(
                    x=main_df['timestamp'] if 'timestamp' in main_df.columns else main_df.index,
                    y=main_df[rsi_col],
                    name=rsi_col,
                    line=dict(width=2)
                ), row=3, col=1)
            
            # Add RSI levels
            fig.add_hline(y=70, line_dash="dash", line_color="red", row=3, col=1)
            fig.add_hline(y=30, line_dash="dash", line_color="green", row=3, col=1)
            fig.add_hline(y=50, line_dash="dot", line_color="gray", row=3, col=1)
        
        # 4. MACD
        if all(col in main_df.columns for col in ['MACD_12_26_9', 'MACD_SIGNAL_12_26_9']):
            fig.add_trace(go.Scatter(
                x=main_df['timestamp'] if 'timestamp' in main_df.columns else main_df.index,
                y=main_df['MACD_12_26_9'],
                name='MACD',
                line=dict(color='blue', width=2)
            ), row=4, col=1)
            
            fig.add_trace(go.Scatter(
                x=main_df['timestamp'] if 'timestamp' in main_df.columns else main_df.index,
                y=main_df['MACD_SIGNAL_12_26_9'],
                name='Signal',
                line=dict(color='red', width=2)
            ), row=4, col=1)
            
            if 'MACD_HIST_12_26_9' in main_df.columns:
                fig.add_trace(go.Bar(
                    x=main_df['timestamp'] if 'timestamp' in main_df.columns else main_df.index,
                    y=main_df['MACD_HIST_12_26_9'],
                    name='MACD Hist',
                    marker_color='gray'
                ), row=4, col=1)
        
        # 5. Custom indicators (ATR, CCI, etc.)
        custom_indicators = ['ATR_14', 'CCI_14', 'WILLR_14', 'ULTOSC']
        available_custom = [col for col in custom_indicators if col in main_df.columns]
        
        if available_custom:
            for idx, indicator in enumerate(available_custom[:2]):  # Max 2
                fig.add_trace(go.Scatter(
                    x=main_df['timestamp'] if 'timestamp' in main_df.columns else main_df.index,
                    y=main_df[indicator],
                    name=indicator,
                    line=dict(width=2)
                ), row=5, col=1)
        
        # Update layout
        fig.update_layout(
            title=f"{symbol} Comprehensive Technical Analysis",
            height=1000,
            showlegend=True,
            legend=dict(
                orientation="v",
                yanchor="top",
                y=1,
                xanchor="left",
                x=1.02
            ),
            hovermode='x unified'
        )
        
        # Update x-axes
        fig.update_xaxes(rangeslider_visible=False)
        
        # Add metadata as annotation
        if main_df.attrs:
            metadata_text = f"Source: {main_df.attrs.get('source', 'Unknown')}<br>"
            metadata_text += f"Timeframe: {main_df.attrs.get('timeframe', 'Unknown')}<br>"
            if 'basic_stats' in main_df.attrs:
                stats = main_df.attrs['basic_stats']
                metadata_text += f"Price Change: {stats.get('price_change_pct', 0):.2f}%"
            
            fig.add_annotation(
                text=metadata_text,
                showarrow=False,
                xref="paper", yref="paper",
                x=0.02, y=0.98,
                bgcolor="rgba(255,255,255,0.8)",
                bordercolor="black",
                borderwidth=1
            )
        
        return fig

# Main Dashboard
def main():
    st.set_page_config(
        page_title="ncOS Comprehensive JSON Visualizer",
        page_icon="📊",
        layout="wide"
    )
    
    st.title("📊 ncOS Comprehensive JSON Data Visualizer")
    st.markdown("---")
    
    # Sidebar
    st.sidebar.title("⚙️ Configuration")
    
    # Symbol selection
    data_path = Path("./data")
    available_symbols = []
    
    if data_path.exists():
        for symbol_dir in data_path.iterdir():
            if symbol_dir.is_dir():
                # Check for any JSON files
                json_files = list(symbol_dir.glob("*.json"))
                if json_files:
                    available_symbols.append(symbol_dir.name)
    
    if not available_symbols:
        st.error("No symbol directories with JSON files found in ./data/")
        st.info("Expected structure: ./data/BTCUSD/BTCUSD_comprehensive.json")
        return
    
    selected_symbol = st.sidebar.selectbox(
        "Select Symbol",
        available_symbols
    )
    
    if selected_symbol:
        session_state["active_symbol"] = selected_symbol
        
        # Scan available files
        available_files = ComprehensiveJSONProcessor.scan_symbol_files(selected_symbol)
        
        if available_files:
            st.sidebar.markdown("### 📁 Available Files")
            for file_type, file_path in available_files.items():
                st.sidebar.text(f"✓ {file_type}")
            
            # Load button
            if st.sidebar.button("🔄 Load/Reload Data"):
                # Load comprehensive file if available
                if 'comprehensive' in available_files:
                    with st.spinner(f"Loading {selected_symbol} comprehensive data..."):
                        try:
                            with open(available_files['comprehensive'], 'r') as f:
                                json_data = json.load(f)
                                session_state["loaded_files"][selected_symbol] = json_data
                                
                                # Extract dataframes
                                dataframes = ComprehensiveJSONProcessor.extract_data_from_comprehensive(json_data)
                                session_state["data_cache"][selected_symbol] = dataframes
                                
                                st.success(f"Loaded {len(dataframes)} data sources from comprehensive file")
                        except Exception as e:
                            st.error(f"Error loading comprehensive file: {e}")
                else:
                    st.warning("No comprehensive JSON file found")
        
        # Main content
        if selected_symbol in session_state["loaded_files"]:
            json_data = session_state["loaded_files"][selected_symbol]
            dataframes = session_state["data_cache"].get(selected_symbol, {})
            
            # Create tabs
            tabs = st.tabs(["📈 Visualization", "📊 Data Analysis", "🔍 Raw Structure", "📋 Summary"])
            
            # Tab 1: Visualization
            with tabs[0]:
                if dataframes:
                    # Create comprehensive plot
                    fig = ComprehensiveJSONProcessor.create_comprehensive_visualization(
                        dataframes, selected_symbol
                    )
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Show available data sources
                    st.subheader("📊 Available Data Sources")
                    
                    cols = st.columns(3)
                    for idx, (source, df) in enumerate(dataframes.items()):
                        with cols[idx % 3]:
                            st.metric(
                                source.replace('_', ' ').title(),
                                f"{len(df)} records",
                                f"{len(df.columns)} features"
                            )
                else:
                    st.warning("No data extracted from comprehensive file")
            
            # Tab 2: Data Analysis
            with tabs[1]:
                if dataframes:
                    st.subheader("📊 Data Source Analysis")
                    
                    # Select data source
                    selected_source = st.selectbox(
                        "Select Data Source",
                        list(dataframes.keys())
                    )
                    
                    if selected_source:
                        df = dataframes[selected_source]
                        
                        # Show dataframe info
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.markdown("#### Data Preview")
                            st.dataframe(df.head(20), use_container_width=True)
                        
                        with col2:
                            st.markdown("#### Column Statistics")
                            numeric_cols = df.select_dtypes(include=[np.number]).columns
                            if len(numeric_cols) > 0:
                                st.dataframe(df[numeric_cols].describe(), use_container_width=True)
                        
                        # Show specific analysis based on source type
                        if 'swing' in selected_source:
                            st.markdown("#### Swing Point Analysis")
                            if 'price' in df.columns:
                                fig = go.Figure()
                                fig.add_trace(go.Scatter(
                                    x=df.index,
                                    y=df['price'],
                                    mode='markers+lines',
                                    name=selected_source
                                ))
                                fig.update_layout(title=f"{selected_source} Distribution")
                                st.plotly_chart(fig, use_container_width=True)
            
            # Tab 3: Raw Structure
            with tabs[2]:
                st.subheader("🔍 JSON Structure Explorer")
                
                # Show structure
                structure = {}
                for key, value in json_data.items():
                    if isinstance(value, dict):
                        structure[key] = {
                            "type": "dict",
                            "keys": list(value.keys())[:10],  # First 10 keys
                            "size": len(value)
                        }
                    elif isinstance(value, list):
                        structure[key] = {
                            "type": "list",
                            "length": len(value),
                            "sample": value[0] if value else None
                        }
                    else:
                        structure[key] = {
                            "type": type(value).__name__,
                            "value": str(value)[:100]
                        }
                
                st.json(structure)
                
                # Raw JSON viewer
                with st.expander("View Raw JSON"):
                    st.json(json_data)
            
            # Tab 4: Summary
            with tabs[3]:
                st.subheader("📋 Analysis Summary")
                
                # Extract key metrics from each source
                for source_file, source_data in json_data.items():
                    if isinstance(source_data, dict) and 'basic_stats' in source_data:
                        st.markdown(f"### {source_file}")
                        
                        stats = source_data['basic_stats']
                        cols = st.columns(4)
                        
                        metrics = [
                            ("First Price", stats.get('first_price', 'N/A')),
                            ("Last Price", stats.get('last_price', 'N/A')),
                            ("Change %", f"{stats.get('price_change_pct', 0):.2f}%"),
                            ("Volatility", f"{stats.get('volatility', 0):.4f}")
                        ]
                        
                        for idx, (label, value) in enumerate(metrics):
                            with cols[idx]:
                                st.metric(label, value)
                        
                        # Additional info
                        info_cols = st.columns(3)
                        with info_cols[0]:
                            st.info(f"**Timeframe**: {source_data.get('timeframe', 'Unknown')}")
                        with info_cols[1]:
                            st.info(f"**Total Bars**: {source_data.get('total_bars', 'Unknown')}")
                        with info_cols[2]:
                            st.info(f"**Duration**: {stats.get('duration_hours', 'Unknown')} hours")
    
    # Footer
    st.sidebar.markdown("---")
    st.sidebar.info("ncOS JSON Visualizer v2.0")
    st.sidebar.caption(f"Session: {datetime.now().strftime('%Y%m%d_%H%M%S')}")

if __name__ == "__main__":
    main()