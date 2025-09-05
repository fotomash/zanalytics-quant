import streamlit as st
import pandas as pd
import numpy as np
import json
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path
import os
from datetime import datetime
from typing import Dict, List, Any, Optional

# ncOS-style session state
session_state = {
    "loaded_symbols": {},
    "active_symbol": None,
    "vector_cache": {},
    "display_mode": "comprehensive"
}

class ComprehensiveJSONVisualizer:
    """ncOS-compatible JSON data visualizer"""
    
    @staticmethod
    def load_json_data(symbol: str) -> Optional[Dict[str, Any]]:
        """Load comprehensive JSON data for symbol"""
        file_path = Path(f"./data/{symbol}/{symbol}_comprehensive.json")
        
        if file_path.exists():
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    session_state["loaded_symbols"][symbol] = data
                    print(f"✓ Loaded {symbol} comprehensive data")
                    return data
            except Exception as e:
                print(f"✗ Error loading {symbol}: {e}")
                return None
        else:
            print(f"✗ File not found: {file_path}")
            return None
    
    @staticmethod
    def extract_dataframe(json_data: Dict[str, Any]) -> pd.DataFrame:
        """Convert JSON to DataFrame with all features"""
        try:
            # Handle different JSON structures
            if 'data' in json_data:
                df = pd.DataFrame(json_data['data'])
            elif 'candles' in json_data:
                df = pd.DataFrame(json_data['candles'])
            elif isinstance(json_data, list):
                df = pd.DataFrame(json_data)
            else:
                # Try to find the main data array
                for key in ['ohlcv', 'bars', 'ticks', 'quotes']:
                    if key in json_data:
                        df = pd.DataFrame(json_data[key])
                        break
                else:
                    df = pd.DataFrame([json_data])
            
            # Ensure timestamp column
            if 'timestamp' in df.columns:
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                df = df.sort_values('timestamp')
            
            # Add derived columns if needed
            if 'close' in df.columns and 'mid' not in df.columns:
                df['mid'] = df['close']
            
            # Extract additional features from JSON
            if 'analysis' in json_data:
                analysis = json_data['analysis']
                for key, value in analysis.items():
                    if isinstance(value, (list, np.ndarray)) and len(value) == len(df):
                        df[f'analysis_{key}'] = value
                    elif isinstance(value, dict):
                        for sub_key, sub_value in value.items():
                            if isinstance(sub_value, (list, np.ndarray)) and len(sub_value) == len(df):
                                df[f'{key}_{sub_key}'] = sub_value
            
            return df
        except Exception as e:
            print(f"DataFrame extraction error: {e}")
            return pd.DataFrame()
    
    @staticmethod
    def create_comprehensive_plot(df: pd.DataFrame, symbol: str, json_data: Dict[str, Any]) -> go.Figure:
        """Create comprehensive multi-panel visualization"""
        
        # Determine available data types
        has_microstructure = any('micro_' in col for col in df.columns)
        has_smc = any('SMC_' in col or 'smc_' in col for col in df.columns)
        has_wyckoff = any('wyckoff_' in col for col in df.columns)
        has_ml = any('ml_' in col or 'prediction' in col for col in df.columns)
        
        # Calculate subplot rows
        num_rows = 3  # Base: price, volume, indicators
        if has_microstructure: num_rows += 1
        if has_smc: num_rows += 1
        if has_wyckoff: num_rows += 1
        if has_ml: num_rows += 1
        
        # Create subplots
        row_heights = [0.4] + [0.15] * (num_rows - 1)
        
        fig = make_subplots(
            rows=num_rows, 
            cols=1,
            shared_xaxes=True,
            vertical_spacing=0.03,
            row_heights=row_heights,
            subplot_titles=[
                f"{symbol} Price Action",
                "Volume Analysis",
                "Technical Indicators"
            ] + (["Microstructure Analysis"] if has_microstructure else []) +
            (["Smart Money Concepts"] if has_smc else []) +
            (["Wyckoff Analysis"] if has_wyckoff else []) +
            (["ML Predictions"] if has_ml else [])
        )
        
        current_row = 1
        
        # 1. Price Chart with overlays
        if 'timestamp' in df.columns:
            # Candlestick chart
            if all(col in df.columns for col in ['open', 'high', 'low', 'close']):
                fig.add_trace(go.Candlestick(
                    x=df['timestamp'],
                    open=df['open'],
                    high=df['high'],
                    low=df['low'],
                    close=df['close'],
                    name='OHLC'
                ), row=current_row, col=1)
            else:
                # Line chart fallback
                fig.add_trace(go.Scatter(
                    x=df['timestamp'],
                    y=df['close'] if 'close' in df.columns else df['mid'],
                    name='Price',
                    line=dict(color='blue')
                ), row=current_row, col=1)
            
            # Add moving averages if available
            for ma_col in ['ma_20', 'ma_50', 'ma_200', 'ema_20', 'ema_50']:
                if ma_col in df.columns:
                    fig.add_trace(go.Scatter(
                        x=df['timestamp'],
                        y=df[ma_col],
                        name=ma_col.upper(),
                        line=dict(width=1)
                    ), row=current_row, col=1)
            
            # Add SMC overlays
            if 'SMC_bullish_ob' in df.columns:
                ob_bulls = df[df['SMC_bullish_ob']]
                if len(ob_bulls) > 0:
                    fig.add_trace(go.Scatter(
                        x=ob_bulls['timestamp'],
                        y=ob_bulls['low'] if 'low' in ob_bulls.columns else ob_bulls['close'],
                        mode='markers',
                        marker=dict(symbol='triangle-up', size=10, color='green'),
                        name='Bullish OB'
                    ), row=current_row, col=1)
            
            if 'SMC_bearish_ob' in df.columns:
                ob_bears = df[df['SMC_bearish_ob']]
                if len(ob_bears) > 0:
                    fig.add_trace(go.Scatter(
                        x=ob_bears['timestamp'],
                        y=ob_bears['high'] if 'high' in ob_bears.columns else ob_bears['close'],
                        mode='markers',
                        marker=dict(symbol='triangle-down', size=10, color='red'),
                        name='Bearish OB'
                    ), row=current_row, col=1)
        
        current_row += 1
        
        # 2. Volume
        if 'volume' in df.columns and 'timestamp' in df.columns:
            colors = ['green' if c >= o else 'red' 
                     for c, o in zip(df['close'], df['open'])] if 'open' in df.columns else 'blue'
            
            fig.add_trace(go.Bar(
                x=df['timestamp'],
                y=df['volume'],
                name='Volume',
                marker_color=colors
            ), row=current_row, col=1)
        
        current_row += 1
        
        # 3. Technical Indicators
        if 'timestamp' in df.columns:
            # RSI
            if 'rsi' in df.columns:
                fig.add_trace(go.Scatter(
                    x=df['timestamp'],
                    y=df['rsi'],
                    name='RSI',
                    line=dict(color='purple')
                ), row=current_row, col=1)
                fig.add_hline(y=70, line_dash="dash", line_color="red", row=current_row, col=1)
                fig.add_hline(y=30, line_dash="dash", line_color="green", row=current_row, col=1)
            
            # MACD
            elif 'macd' in df.columns:
                fig.add_trace(go.Scatter(
                    x=df['timestamp'],
                    y=df['macd'],
                    name='MACD',
                    line=dict(color='blue')
                ), row=current_row, col=1)
                if 'macd_signal' in df.columns:
                    fig.add_trace(go.Scatter(
                        x=df['timestamp'],
                        y=df['macd_signal'],
                        name='Signal',
                        line=dict(color='red')
                    ), row=current_row, col=1)
        
        current_row += 1
        
        # 4. Microstructure Analysis
        if has_microstructure and 'timestamp' in df.columns:
            # Order flow imbalance
            if 'micro_order_flow_imbalance' in df.columns:
                fig.add_trace(go.Scatter(
                    x=df['timestamp'],
                    y=df['micro_order_flow_imbalance'],
                    name='Order Flow Imbalance',
                    line=dict(color='orange')
                ), row=current_row, col=1)
            
            # Manipulation score
            if 'micro_manipulation_score' in df.columns:
                fig.add_trace(go.Scatter(
                    x=df['timestamp'],
                    y=df['micro_manipulation_score'],
                    name='Manipulation Score',
                    line=dict(color='red'),
                    yaxis='y2'
                ), row=current_row, col=1)
            
            # Stop hunts
            if 'micro_stop_hunt' in df.columns:
                stop_hunts = df[df['micro_stop_hunt']]
                if len(stop_hunts) > 0:
                    fig.add_trace(go.Scatter(
                        x=stop_hunts['timestamp'],
                        y=[0.5] * len(stop_hunts),
                        mode='markers',
                        marker=dict(symbol='x', size=12, color='red'),
                        name='Stop Hunts'
                    ), row=current_row, col=1)
            
            current_row += 1
        
        # 5. Smart Money Concepts
        if has_smc and 'timestamp' in df.columns:
            # Market structure
            if 'SMC_structure' in df.columns:
                structure_map = {'bullish': 1, 'bearish': -1, 'neutral': 0}
                structure_values = df['SMC_structure'].map(structure_map).fillna(0)
                
                fig.add_trace(go.Scatter(
                    x=df['timestamp'],
                    y=structure_values,
                    name='Market Structure',
                    line=dict(color='blue', width=2),
                    fill='tozeroy'
                ), row=current_row, col=1)
            
            # FVG indicators
            if 'SMC_fvg_bullish' in df.columns:
                fvg_bulls = df[df['SMC_fvg_bullish']]
                if len(fvg_bulls) > 0:
                    fig.add_trace(go.Scatter(
                        x=fvg_bulls['timestamp'],
                        y=[0.5] * len(fvg_bulls),
                        mode='markers',
                        marker=dict(symbol='square', size=8, color='green'),
                        name='Bullish FVG'
                    ), row=current_row, col=1)
            
            current_row += 1
        
        # 6. Wyckoff Analysis
        if has_wyckoff and 'timestamp' in df.columns:
            # Wyckoff phases
            if 'wyckoff_phase' in df.columns:
                phase_map = {
                    'accumulation': 1, 
                    'markup': 2, 
                    'distribution': -1, 
                    'markdown': -2,
                    'neutral': 0
                }
                phase_values = df['wyckoff_phase'].map(phase_map).fillna(0)
                
                fig.add_trace(go.Scatter(
                    x=df['timestamp'],
                    y=phase_values,
                    name='Wyckoff Phase',
                    line=dict(color='purple', width=2),
                    fill='tozeroy'
                ), row=current_row, col=1)
            
            # Springs and upthrusts
            if 'wyckoff_spring' in df.columns:
                springs = df[df['wyckoff_spring']]
                if len(springs) > 0:
                    fig.add_trace(go.Scatter(
                        x=springs['timestamp'],
                        y=[1] * len(springs),
                        mode='markers',
                        marker=dict(symbol='triangle-up', size=12, color='green'),
                        name='Springs'
                    ), row=current_row, col=1)
            
            current_row += 1
        
        # 7. ML Predictions
        if has_ml and 'timestamp' in df.columns:
            # Find prediction columns
            pred_cols = [col for col in df.columns if 'prediction' in col or 'ml_signal' in col]
            for pred_col in pred_cols[:2]:  # Max 2 predictions
                fig.add_trace(go.Scatter(
                    x=df['timestamp'],
                    y=df[pred_col],
                    name=pred_col.replace('_', ' ').title(),
                    line=dict(width=2)
                ), row=current_row, col=1)
        
        # Update layout
        fig.update_layout(
            title=f"{symbol} Comprehensive Analysis Dashboard",
            height=300 * num_rows,
            showlegend=True,
            legend=dict(x=1.02, y=1),
            margin=dict(r=150),
            hovermode='x unified'
        )
        
        # Update x-axes
        fig.update_xaxes(rangeslider_visible=False)
        
        return fig
    
    @staticmethod
    def extract_metadata(json_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract metadata and statistics from JSON"""
        metadata = {
            "timestamp_range": None,
            "total_records": 0,
            "available_features": [],
            "analysis_modules": [],
            "statistics": {}
        }
        
        try:
            # Get main data
            df = ComprehensiveJSONVisualizer.extract_dataframe(json_data)
            
            if not df.empty:
                metadata["total_records"] = len(df)
                metadata["available_features"] = list(df.columns)
                
                if 'timestamp' in df.columns:
                    metadata["timestamp_range"] = {
                        "start": str(df['timestamp'].min()),
                        "end": str(df['timestamp'].max()),
                        "duration": str(df['timestamp'].max() - df['timestamp'].min())
                    }
                
                # Extract statistics
                numeric_cols = df.select_dtypes(include=[np.number]).columns
                for col in numeric_cols:
                    if col not in ['timestamp', 'index']:
                        metadata["statistics"][col] = {
                            "mean": float(df[col].mean()),
                            "std": float(df[col].std()),
                            "min": float(df[col].min()),
                            "max": float(df[col].max())
                        }
            
            # Extract analysis modules
            if 'analysis' in json_data:
                metadata["analysis_modules"] = list(json_data['analysis'].keys())
            
            # Extract any metadata from JSON
            if 'metadata' in json_data:
                metadata.update(json_data['metadata'])
            
        except Exception as e:
            print(f"Metadata extraction error: {e}")
        
        return metadata

# Streamlit Dashboard
def main():
    st.set_page_config(
        page_title="ncOS JSON Data Visualizer",
        page_icon="📊",
        layout="wide"
    )
    
    st.title("🔍 Comprehensive JSON Data Visualizer")
    st.markdown("---")
    
    # Sidebar for file selection
    st.sidebar.title("📁 Data Selection")
    
    # Scan for available symbols
    data_path = Path("./data")
    available_symbols = []
    
    if data_path.exists():
        for symbol_dir in data_path.iterdir():
            if symbol_dir.is_dir():
                json_file = symbol_dir / f"{symbol_dir.name}_comprehensive.json"
                if json_file.exists():
                    available_symbols.append(symbol_dir.name)
    
    if not available_symbols:
        st.warning("No comprehensive JSON files found in ./data/{symbol}/{symbol}_comprehensive.json")
        st.info("Expected structure: ./data/BTCUSD/BTCUSD_comprehensive.json")
        return
    
    # Symbol selection
    selected_symbol = st.sidebar.selectbox(
        "Select Symbol",
        available_symbols,
        index=0 if available_symbols else None
    )
    
    if selected_symbol:
        session_state["active_symbol"] = selected_symbol
        
        # Load data button
        if st.sidebar.button("🔄 Load/Reload Data"):
            with st.spinner(f"Loading {selected_symbol} data..."):
                ComprehensiveJSONVisualizer.load_json_data(selected_symbol)
        
        # Check if data is loaded
        if selected_symbol in session_state["loaded_symbols"]:
            json_data = session_state["loaded_symbols"][selected_symbol]
            df = ComprehensiveJSONVisualizer.extract_dataframe(json_data)
            
            if not df.empty:
                # Display metadata
                with st.sidebar.expander("📊 Data Overview", expanded=True):
                    metadata = ComprehensiveJSONVisualizer.extract_metadata(json_data)
                    st.json(metadata)
                
                # Main visualization tabs
                tab1, tab2, tab3, tab4 = st.tabs([
                    "📈 Comprehensive Chart", 
                    "📊 Data Analysis", 
                    "🔍 Feature Explorer",
                    "📝 Raw Data"
                ])
                
                with tab1:
                    # Comprehensive chart
                    fig = ComprehensiveJSONVisualizer.create_comprehensive_plot(
                        df, selected_symbol, json_data
                    )
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Quick stats
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        if 'close' in df.columns:
                            latest_price = df['close'].iloc[-1]
                            price_change = df['close'].pct_change().iloc[-1] * 100
                            st.metric(
                                "Latest Price", 
                                f"{latest_price:.4f}",
                                f"{price_change:+.2f}%"
                            )
                    
                    with col2:
                        if 'micro_manipulation_score' in df.columns:
                            manip_score = df['micro_manipulation_score'].mean()
                            st.metric(
                                "Avg Manipulation",
                                f"{manip_score:.3f}",
                                "High" if manip_score > 0.5 else "Normal"
                            )
                    
                    with col3:
                        if 'SMC_structure' in df.columns:
                            structure = df['SMC_structure'].iloc[-1]
                            st.metric("Market Structure", structure.upper())
                    
                    with col4:
                        if 'wyckoff_phase' in df.columns:
                            phase = df['wyckoff_phase'].value_counts().index[0]
                            st.metric("Dominant Phase", phase.upper())
                
                with tab2:
                    st.subheader("📊 Statistical Analysis")
                    
                    # Feature categories
                    feature_categories = {
                        "Price Data": ['open', 'high', 'low', 'close', 'mid'],
                        "Volume": ['volume', 'volume_ma', 'volume_std'],
                        "Microstructure": [col for col in df.columns if 'micro_' in col],
                        "SMC": [col for col in df.columns if 'SMC_' in col or 'smc_' in col],
                        "Wyckoff": [col for col in df.columns if 'wyckoff_' in col],
                        "ML/Predictions": [col for col in df.columns if 'ml_' in col or 'prediction' in col],
                        "Technical": ['rsi', 'macd', 'ma_', 'ema_', 'bb_']
                    }
                    
                    for category, cols in feature_categories.items():
                        available_cols = [col for col in cols if col in df.columns]
                        if available_cols:
                            st.markdown(f"#### {category}")
                            
                            # Create summary statistics
                            stats_df = df[available_cols].describe()
                            st.dataframe(stats_df, use_container_width=True)
                            
                            # Correlation matrix
                            if len(available_cols) > 1:
                                corr = df[available_cols].corr()
                                fig_corr = go.Figure(data=go.Heatmap(
                                    z=corr.values,
                                    x=corr.columns,
                                    y=corr.columns,
                                    colorscale='RdBu',
                                    zmid=0
                                ))
                                fig_corr.update_layout(
                                    title=f"{category} Correlation Matrix",
                                    height=400
                                )
                                st.plotly_chart(fig_corr, use_container_width=True)
                
                with tab3:
                    st.subheader("🔍 Feature Explorer")
                    
                    # Feature selector
                    all_numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
                    selected_features = st.multiselect(
                        "Select features to explore",
                        all_numeric_cols,
                        default=all_numeric_cols[:5] if len(all_numeric_cols) > 5 else all_numeric_cols
                    )
                    
                    if selected_features:
                        # Time series plot
                        fig_ts = go.Figure()
                        for feature in selected_features:
                            fig_ts.add_trace(go.Scatter(
                                x=df['timestamp'] if 'timestamp' in df.columns else df.index,
                                y=df[feature],
                                name=feature,
                                mode='lines'
                            ))
                        
                        fig_ts.update_layout(
                            title="Feature Time Series",
                            height=500,
                            hovermode='x unified'
                        )
                        st.plotly_chart(fig_ts, use_container_width=True)
                        
                        # Distribution plots
                        cols = st.columns(min(3, len(selected_features)))
                        for idx, feature in enumerate(selected_features[:3]):
                            with cols[idx]:
                                fig_dist = go.Figure()
                                fig_dist.add_trace(go.Histogram(
                                    x=df[feature],
                                    name=feature,
                                    nbinsx=50
                                ))
                                fig_dist.update_layout(
                                    title=f"{feature} Distribution",
                                    height=300
                                )
                                st.plotly_chart(fig_dist, use_container_width=True)
                
                with tab4:
                    st.subheader("📝 Raw Data View")
                    
                    # Display options
                    col1, col2 = st.columns(2)
                    with col1:
                        show_head = st.checkbox("Show first N rows", True)
                        if show_head:
                            n_rows = st.number_input("Number of rows", 5, 100, 20)
                            st.dataframe(df.head(n_rows), use_container_width=True)
                    
                    with col2:
                        show_tail = st.checkbox("Show last N rows", False)
                        if show_tail:
                            n_rows_tail = st.number_input("Number of rows (tail)", 5, 100, 20)
                            st.dataframe(df.tail(n_rows_tail), use_container_width=True)
                    
                    # Download button
                    csv = df.to_csv(index=False)
                    st.download_button(
                        label="📥 Download as CSV",
                        data=csv,
                        file_name=f"{selected_symbol}_data.csv",
                        mime="text/csv"
                    )
                    
                    # Show raw JSON structure
                    with st.expander("🔧 Raw JSON Structure"):
                        # Show keys and structure
                        st.json({
                            k: f"<{type(v).__name__} with {len(v) if isinstance(v, (list, dict)) else 'N/A'} items>"
                            for k, v in json_data.items()
                        })
            else:
                st.error(f"Failed to extract data from {selected_symbol} JSON file")
        else:
            st.info(f"Click 'Load/Reload Data' to load {selected_symbol} data")
    
    # Footer
    st.sidebar.markdown("---")
    st.sidebar.info("ncOS JSON Visualizer v1.0")
    st.sidebar.caption(f"Session ID: {datetime.now().strftime('%Y%m%d_%H%M%S')}")

if __name__ == "__main__":
    main()