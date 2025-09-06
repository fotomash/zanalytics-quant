import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import json
import os
import glob
from datetime import datetime, timedelta
import numpy as np
from typing import Dict, List, Optional, Tuple
import warnings
warnings.filterwarnings('ignore')

# Page config
st.set_page_config(
    page_title="ncOS SMC Ultimate Intelligence",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for ultimate SMC styling
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
        padding: 2rem;
        border-radius: 20px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
        box-shadow: 0 10px 40px rgba(0,0,0,0.2);
    }
.smc-metric {
    background: #222e3a;
    color: #e7eaf0;
    padding: 0.45rem 0.7rem;
    border-radius: 6px;
    border: 1px solid #263246;
    box-shadow: 0 1px 3px rgba(20,30,40,0.09);
    text-align: center;
    min-width: 90px;
    max-width: 120px;
    font-size: 0.93rem;
    margin: 0;
    display: flex;
    flex-direction: column;
    align-items: center;
}
.smc-metric h2 {
    font-size: 1rem;
    font-weight: 600;
    margin: 0.18rem 0 0.07rem 0;
}
.smc-metric h3 {
    font-size: 0.92rem;
    font-weight: 500;
    margin-bottom: 0.04rem;
}
.smc-metric p {
    font-size: 0.81rem;
    margin: 0.08rem 0;
}
    .order-block-card {
        background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        margin: 0.5rem 0;
    }
    .liquidity-card {
        background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        margin: 0.5rem 0;
    }
    .wyckoff-phase {
        background: linear-gradient(135deg, #fa709a 0%, #fee140 100%);
        padding: 1rem;
        border-radius: 10px;
        color: #2c3e50;
        margin: 0.5rem 0;
        font-weight: bold;
    }
    .signal-alert {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        padding: 1.2rem;
        border-radius: 12px;
        color: white;
        margin: 1rem 0;
        box-shadow: 0 5px 25px rgba(0,0,0,0.3);
        animation: pulse 2s infinite;
    }
    @keyframes pulse {
        0% { transform: scale(1); }
        50% { transform: scale(1.02); }
        100% { transform: scale(1); }
    }
    .data-status {
        background: #2c3e50;
        color: #ecf0f1;
        padding: 0.5rem 1rem;
        border-radius: 20px;
        font-size: 0.9rem;
        display: inline-block;
        margin: 0.2rem;
    }
</style>
""", unsafe_allow_html=True)

# Configuration
class UltimateSMCConfig:
    def __init__(self):
        self.data_dir = "./data"
        self.max_bars = 1500
        self.pairs = ["XAUUSD", "BTCUSD", "GBPUSD"]
        self.timeframes = ["1T", "5T", "15T", "30T", "1H"]
        self.timeframe_map = {
            "1T": "1 Minute",
            "5T": "5 Minutes",
            "15T": "15 Minutes", 
            "30T": "30 Minutes",
            "1H": "1 Hour"
        }
        self.colors = {
            'bullish': '#26de81',
            'bearish': '#fc5c65',
            'bullish_ob': 'rgba(38, 222, 129, 0.3)',
            'bearish_ob': 'rgba(252, 92, 101, 0.3)',
            'supply': 'rgba(255, 107, 107, 0.2)',
            'demand': 'rgba(46, 213, 115, 0.2)',
            'liquidity': '#45aaf2',
            'fvg_bull': 'rgba(162, 155, 254, 0.2)',
            'fvg_bear': 'rgba(253, 121, 168, 0.2)',
            'poc': '#f39c12',
            'value_area': 'rgba(243, 156, 18, 0.1)',
            'harmonic': '#9b59b6',
            'wyckoff_acc': '#00cec9',
            'wyckoff_dist': '#e17055'
        }

# Data Loader
class SMCDataLoader:
    def __init__(self, config):
        self.config = config
        
    def scan_data_directory(self):
        """Scan data directory for comprehensive and summary files"""
        pairs_data = {}
        
        # Look for CSV files (comprehensive data)
        csv_files = glob.glob(os.path.join(self.config.data_dir, "**", "*.csv"), recursive=True)
        
        # Look for JSON files (summary data)
        json_files = glob.glob(os.path.join(self.config.data_dir, "**", "*.json"), recursive=True)
        
        # Process each pair
        for pair in self.config.pairs:
            pairs_data[pair] = {
                'comprehensive_files': {},
                'summary_files': {}
            }
            
            # Find comprehensive files for each timeframe
            for tf in self.config.timeframes:
                # Find comprehensive files
                comp_files = [f for f in csv_files if pair in f and (f"_{tf}" in f or f"_{tf.lower()}" in f)]
                if comp_files:
                    pairs_data[pair]['comprehensive_files'][tf] = comp_files[-1]  # Use the latest file
                
                # Find summary files
                summary_files = [f for f in json_files if pair in f and (f"_{tf}" in f or f"_{tf.lower()}" in f)]
                if summary_files:
                    pairs_data[pair]['summary_files'][tf] = summary_files[-1]  # Use the latest file
        
        return pairs_data
    
    def load_comprehensive_data(self, file_path, max_bars=None):
        """Load comprehensive data from CSV file"""
        try:
            # Try comma-separated first
            df = pd.read_csv(file_path)
            
            # If doesn't have expected columns, try tab-separated
            if 'open' not in df.columns and 'high' not in df.columns:
                df = pd.read_csv(file_path, sep='	')
            
            # Convert timestamp to datetime if it exists
            if 'timestamp' in df.columns:
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                df.set_index('timestamp', inplace=True)
            
            # Limit the number of bars if specified
            if max_bars and len(df) > max_bars:
                df = df.iloc[-max_bars:]
            
            return df
        except Exception as e:
            st.error(f"Error loading data: {str(e)}")
            return None
    
    def load_smc_summary(self, file_path):
        """Load SMC summary from JSON file"""
        try:
            with open(file_path, 'r') as f:
                summary = json.load(f)
            return summary
        except Exception as e:
            st.error(f"Error loading summary: {str(e)}")
            return {}
    
    def extract_all_smc_features(self, df, summary):
        """Extract all SMC features from dataframe and summary"""
        # Initialize features dictionary
        features = {
            'order_blocks': [],
            'liquidity_zones': [],
            'fair_value_gaps': [],
            'supply_demand_zones': {'supply': [], 'demand': []},
            'bos_choch_points': {'bos': [], 'choch': []},
            'pivot_points': {'highs': [], 'lows': []},
            'market_structure': {'trend': 'neutral', 'strength': 50},
            'volume_profile': {'poc': None, 'vah': None, 'val': None},
            'harmonic_patterns': [],
            'wyckoff_analysis': {'phase': 'Unknown', 'events': [], 'accumulation_zones': [], 'distribution_zones': []},
            'signals': []
        }
        
        # Extract features from summary if available
        if summary:
            # Order blocks
            if 'order_blocks' in summary:
                features['order_blocks'] = summary['order_blocks']
            
            # Liquidity zones
            if 'liquidity_zones' in summary:
                features['liquidity_zones'] = summary['liquidity_zones']
            
            # Fair value gaps
            if 'fair_value_gaps' in summary:
                features['fair_value_gaps'] = summary['fair_value_gaps']
            
            # Supply/demand zones
            if 'supply_demand_zones' in summary:
                # Handle both list and dictionary formats
                if isinstance(summary['supply_demand_zones'], dict):
                    features['supply_demand_zones'] = summary['supply_demand_zones']
                else:
                    # Convert list to dict format
                    supply = [z for z in summary['supply_demand_zones'] if z.get('type') == 'supply']
                    demand = [z for z in summary['supply_demand_zones'] if z.get('type') == 'demand']
                    features['supply_demand_zones'] = {'supply': supply, 'demand': demand}
            
            # BOS/CHoCH points
            if 'bos_choch_points' in summary:
                features['bos_choch_points'] = summary['bos_choch_points']
            
            # Pivot points
            if 'pivot_points' in summary:
                features['pivot_points'] = summary['pivot_points']
            
            # Market structure
            if 'market_structure' in summary:
                features['market_structure'] = summary['market_structure']
            
            # Volume profile
            if 'volume_profile' in summary:
                features['volume_profile'] = summary['volume_profile']
            
            # Harmonic patterns
            if 'harmonic_patterns' in summary:
                features['harmonic_patterns'] = summary['harmonic_patterns']
            
            # Wyckoff analysis
            if 'wyckoff_analysis' in summary:
                features['wyckoff_analysis'] = summary['wyckoff_analysis']
            
            # Signals
            if 'signals' in summary:
                features['signals'] = summary['signals']
        
        # If no summary or missing features, try to extract from dataframe
        if not features['market_structure']['trend'] or features['market_structure']['trend'] == 'neutral':
            # Simple trend detection
            if len(df) > 20:
                sma20 = df['close'].rolling(20).mean()
                sma50 = df['close'].rolling(50).mean()
                
                if sma20.iloc[-1] > sma50.iloc[-1]:
                    features['market_structure']['trend'] = 'bullish'
                    features['market_structure']['strength'] = 70
                else:
                    features['market_structure']['trend'] = 'bearish'
                    features['market_structure']['strength'] = 70
        
        # If no volume profile, calculate simple one
        if not features['volume_profile']['poc']:
            if 'volume' in df.columns and len(df) > 0:
                # Simple POC calculation
                price_bins = pd.cut(df['close'], bins=10)
                volume_profile = df.groupby(price_bins)['volume'].sum()
                max_vol_bin = volume_profile.idxmax()
                
                features['volume_profile']['poc'] = max_vol_bin.mid
                features['volume_profile']['vah'] = max_vol_bin.right
                features['volume_profile']['val'] = max_vol_bin.left
        
        return features

# Chart Generator
class SMCChartGenerator:
    def __init__(self, config):
        self.config = config
    
    def create_ultimate_smc_chart(self, df, features, pair, timeframe_name):
        """Create ultimate SMC chart with all features"""
        # Create figure with secondary y-axis
        fig = make_subplots(
            rows=2, 
            cols=1, 
            shared_xaxes=True,
            vertical_spacing=0.05,
            row_heights=[0.8, 0.2],
            subplot_titles=(f"{pair} - {timeframe_name} - SMC Analysis", "Volume")
        )
        
        # Add candlestick chart
        fig.add_trace(
            go.Candlestick(
                x=df.index,
                open=df['open'],
                high=df['high'],
                low=df['low'],
                close=df['close'],
                name="Price"
            ),
            row=1, col=1
        )
        
        # Add volume
        if 'volume' in df.columns:
            colors = [self.config.colors['bullish'] if row['close'] >= row['open'] else self.config.colors['bearish'] 
                     for _, row in df.iterrows()]
            
            fig.add_trace(
                go.Bar(
                    x=df.index,
                    y=df['volume'],
                    marker_color=colors,
                    name="Volume"
                ),
                row=2, col=1
            )
        
        # Add order blocks
        for ob in features['order_blocks']:
            color = self.config.colors['bullish_ob'] if ob.get('type') == 'bullish' else self.config.colors['bearish_ob']
            
            fig.add_shape(
                type="rect",
                x0=ob.get('start_time', df.index[0]),
                x1=ob.get('end_time', df.index[-1]),
                y0=ob.get('low', 0),
                y1=ob.get('high', 0),
                fillcolor=color,
                opacity=0.7,
                line=dict(width=0),
                row=1, col=1
            )
            
            # Add annotation
            fig.add_annotation(
                x=ob.get('end_time', df.index[-1]),
                y=ob.get('high', 0),
                text=f"OB {ob.get('type', '')}",
                showarrow=True,
                arrowhead=2,
                row=1, col=1
            )
        
        # Add liquidity zones
        for lz in features['liquidity_zones']:
            fig.add_shape(
                type="line",
                x0=df.index[0],
                x1=df.index[-1],
                y0=lz.get('level', 0),
                y1=lz.get('level', 0),
                line=dict(
                    color=self.config.colors['liquidity'],
                    width=2,
                    dash="dash"
                ),
                row=1, col=1
            )
            
            # Add annotation
            fig.add_annotation(
                x=df.index[-1],
                y=lz.get('level', 0),
                text=f"LIQ {lz.get('type', '')}",
                showarrow=True,
                arrowhead=2,
                row=1, col=1
            )
        
        # Add fair value gaps
        for fvg in features['fair_value_gaps']:
            color = self.config.colors['fvg_bull'] if fvg.get('type') == 'bullish' else self.config.colors['fvg_bear']
            
            fig.add_shape(
                type="rect",
                x0=fvg.get('start_time', df.index[0]),
                x1=fvg.get('end_time', df.index[-1]),
                y0=fvg.get('low', 0),
                y1=fvg.get('high', 0),
                fillcolor=color,
                opacity=0.5,
                line=dict(width=0),
                row=1, col=1
            )
        
        # Add supply/demand zones
        for supply in features['supply_demand_zones'].get('supply', []):
            fig.add_shape(
                type="rect",
                x0=supply.get('start_time', df.index[0]),
                x1=supply.get('end_time', df.index[-1]),
                y0=supply.get('low', 0),
                y1=supply.get('high', 0),
                fillcolor=self.config.colors['supply'],
                opacity=0.7,
                line=dict(width=0),
                row=1, col=1
            )
        
        for demand in features['supply_demand_zones'].get('demand', []):
            fig.add_shape(
                type="rect",
                x0=demand.get('start_time', df.index[0]),
                x1=demand.get('end_time', df.index[-1]),
                y0=demand.get('low', 0),
                y1=demand.get('high', 0),
                fillcolor=self.config.colors['demand'],
                opacity=0.7,
                line=dict(width=0),
                row=1, col=1
            )
        
        # Add BOS/CHoCH points
        for bos in features['bos_choch_points'].get('bos', []):
            fig.add_trace(
                go.Scatter(
                    x=[bos.get('time', df.index[0])],
                    y=[bos.get('price', 0)],
                    mode='markers',
                    marker=dict(
                        symbol='triangle-up' if bos.get('direction') == 'up' else 'triangle-down',
                        size=12,
                        color='green' if bos.get('direction') == 'up' else 'red',
                        line=dict(width=2, color='white')
                    ),
                    name=f"BOS {bos.get('direction', '')}"
                ),
                row=1, col=1
            )
        
        for choch in features['bos_choch_points'].get('choch', []):
            fig.add_trace(
                go.Scatter(
                    x=[choch.get('time', df.index[0])],
                    y=[choch.get('price', 0)],
                    mode='markers',
                    marker=dict(
                        symbol='star',
                        size=12,
                        color='purple',
                        line=dict(width=2, color='white')
                    ),
                    name=f"CHoCH {choch.get('direction', '')}"
                ),
                row=1, col=1
            )
        
        # Add volume profile
        if features['volume_profile']['poc']:
            # POC line
            fig.add_shape(
                type="line",
                x0=df.index[0],
                x1=df.index[-1],
                y0=features['volume_profile']['poc'],
                y1=features['volume_profile']['poc'],
                line=dict(
                    color=self.config.colors['poc'],
                    width=2
                ),
                row=1, col=1
            )
            
            # Value area
            if features['volume_profile']['vah'] and features['volume_profile']['val']:
                fig.add_shape(
                    type="rect",
                    x0=df.index[0],
                    x1=df.index[-1],
                    y0=features['volume_profile']['val'],
                    y1=features['volume_profile']['vah'],
                    fillcolor=self.config.colors['value_area'],
                    opacity=0.3,
                    line=dict(width=0),
                    row=1, col=1
                )
        
        # Add harmonic patterns
        for pattern in features['harmonic_patterns']:
            # Connect pattern points
            points_x = [pattern.get(f'point{i}_time', df.index[0]) for i in range(1, 5) if f'point{i}_time' in pattern]
            points_y = [pattern.get(f'point{i}_price', 0) for i in range(1, 5) if f'point{i}_price' in pattern]
            
            if len(points_x) >= 3 and len(points_y) >= 3:
                fig.add_trace(
                    go.Scatter(
                        x=points_x,
                        y=points_y,
                        mode='lines+markers',
                        line=dict(color=self.config.colors['harmonic'], width=2),
                        marker=dict(size=8),
                        name=f"Harmonic: {pattern.get('pattern_type', 'Unknown')}"
                    ),
                    row=1, col=1
                )
        
        # Add Wyckoff phases
        for acc_zone in features['wyckoff_analysis'].get('accumulation_zones', []):
            fig.add_shape(
                type="rect",
                x0=acc_zone.get('start_time', df.index[0]),
                x1=acc_zone.get('end_time', df.index[-1]),
                y0=acc_zone.get('low', 0),
                y1=acc_zone.get('high', 0),
                fillcolor=self.config.colors['wyckoff_acc'],
                opacity=0.3,
                line=dict(width=0),
                row=1, col=1
            )
        
        for dist_zone in features['wyckoff_analysis'].get('distribution_zones', []):
            fig.add_shape(
                type="rect",
                x0=dist_zone.get('start_time', df.index[0]),
                x1=dist_zone.get('end_time', df.index[-1]),
                y0=dist_zone.get('low', 0),
                y1=dist_zone.get('high', 0),
                fillcolor=self.config.colors['wyckoff_dist'],
                opacity=0.3,
                line=dict(width=0),
                row=1, col=1
            )
        
        # Add signals
        for signal in features['signals']:
            marker_color = 'green' if signal.get('type') == 'buy' else 'red'
            marker_symbol = 'triangle-up' if signal.get('type') == 'buy' else 'triangle-down'
            
            fig.add_trace(
                go.Scatter(
                    x=[signal.get('timestamp', df.index[0])],
                    y=[signal.get('price', 0)],
                    mode='markers',
                    marker=dict(
                        symbol=marker_symbol,
                        size=12,
                        color=marker_color,
                        line=dict(width=2, color='white')
                    ),
                    name=f"Signal: {signal.get('type', '').upper()}"
                ),
                row=1, col=1
            )
        
        # Update layout
        fig.update_layout(
            title=f"{pair} - {timeframe_name} - Ultimate SMC Analysis",
            xaxis_title="Time",
            yaxis_title="Price",
            xaxis_rangeslider_visible=False,
            template="plotly_dark",
            height=800,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            )
        )
        
        # Update y-axis
        fig.update_yaxes(title_text="Price", row=1, col=1)
        fig.update_yaxes(title_text="Volume", row=2, col=1)
        
        return fig

def main():
    # Initialize config
    config = UltimateSMCConfig()
    
    # Initialize data loader and chart generator
    loader = SMCDataLoader(config)
    chart_gen = SMCChartGenerator(config)
    
    # (Header removed as per instructions)
    
    # Scan data directory
    pairs_data = loader.scan_data_directory()
    
    # Sidebar
    st.sidebar.title("🔧 Configuration")
    
    # Pair selection
    available_pairs = [pair for pair in pairs_data.keys() if any(pairs_data[pair]['comprehensive_files'].values())]
    
    if not available_pairs:
        st.error("❌ No data files found. Please check your data directory.")
        return
    
    selected_pair = st.sidebar.selectbox("Select Pair", available_pairs)
    
    # Timeframe selection
    available_tfs = [tf for tf, file in pairs_data[selected_pair]['comprehensive_files'].items() if file]
    
    if not available_tfs:
        st.error(f"❌ No data files found for {selected_pair}. Please check your data directory.")
        return
    
    selected_tf = st.sidebar.selectbox("Select Timeframe", available_tfs)
    
    # Max bars
    max_bars = st.sidebar.slider("Max Bars to Display", 100, 5000, config.max_bars)
    
    # Feature toggles
    st.sidebar.markdown("### 🎚️ Feature Toggles")
    
    col1, col2 = st.sidebar.columns(2)
    
    with col1:
        show_order_blocks = st.checkbox("Order Blocks", value=True)
        show_liquidity = st.checkbox("Liquidity Zones", value=True)
        show_supply_demand = st.checkbox("Supply/Demand", value=True)
        show_fvg = st.checkbox("Fair Value Gaps", value=True)
        show_structure = st.checkbox("Market Structure", value=True)
    
    with col2:
        show_pivots = st.checkbox("Pivot Points", value=True)
        show_volume_profile = st.checkbox("Volume Profile", value=True)
        show_harmonics = st.checkbox("Harmonic Patterns", value=True)
        show_wyckoff = st.checkbox("Wyckoff Analysis", value=True)
        show_signals = st.checkbox("Trading Signals", value=True)
    
    # Data status
    st.sidebar.markdown("### 📊 Data Status")
    
    pair_info = pairs_data[selected_pair]
    
    # Show data status
    st.sidebar.markdown(f"""
    <div>
        <span class="data-status">📈 Comprehensive: {len(pair_info['comprehensive_files'])} files</span>
        <span class="data-status">📋 Summary: {len(pair_info['summary_files'])} files</span>
    </div>
    """, unsafe_allow_html=True)
    
    # Main content
    if selected_pair and selected_tf:
        # Load COMPREHENSIVE data
        comp_file = pair_info['comprehensive_files'].get(selected_tf)
        summary_file = pair_info['summary_files'].get(selected_tf)
        
        if not comp_file:
            st.error(f"❌ No COMPREHENSIVE data for {selected_pair} {selected_tf}")
            return
        
        with st.spinner(f"🔄 Loading {selected_pair} {selected_tf} COMPREHENSIVE data..."):
            # Load data
            df = loader.load_comprehensive_data(comp_file, max_bars)
            
            if df is None:
                st.error("❌ Failed to load data")
                return
            
            # Load summary
            summary = {}
            if summary_file:
                summary = loader.load_smc_summary(summary_file)
            
            # Extract ALL SMC features
            smc_features = loader.extract_all_smc_features(df, summary)
        
        # Display metrics as a compact Streamlit table
        current_price = df['close'].iloc[-1]
        prev_close = df['close'].iloc[-2] if len(df) > 1 else current_price
        change = current_price - prev_close
        change_pct = (change / prev_close * 100) if prev_close != 0 else 0
        market_structure = smc_features['market_structure']
        order_blocks_count = len(smc_features['order_blocks'])
        liquidity_count = len(smc_features['liquidity_zones'])
        wyckoff_phase = smc_features['wyckoff_analysis']['phase']
        signals_count = len(smc_features['signals'])
        buy_signals = sum(1 for s in smc_features['signals'] if s.get('type') == 'buy')
        sell_signals = signals_count - buy_signals
        metric_table = {
            "Metric": ["Price", "Change", "Trend", "SMC Levels", "Wyckoff Phase", "Signals"],
            "Value": [
                f"{current_price:.5f}",
                f"{change:+.5f} ({change_pct:+.2f}%)",
                f"{market_structure['trend'].capitalize()}",
                f"OB: {order_blocks_count}, LIQ: {liquidity_count}",
                wyckoff_phase,
                f"Buy: {buy_signals}, Sell: {sell_signals}"
            ]
        }
        st.markdown("### 🔹 Market Snapshot")
        st.table(pd.DataFrame(metric_table))
        
        # Key insights
        st.markdown("### 🔍 Key SMC Insights")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if smc_features['order_blocks']:
                latest_ob = smc_features['order_blocks'][-1]
                ob_type = latest_ob.get('type', 'unknown')
                
                st.markdown(f"""
                <div class="order-block-card">
                    <h4>📦 Latest Order Block</h4>
                    <p>Type: <strong>{ob_type.upper()}</strong></p>
                    <p>Level: {latest_ob.get('high', 0):.5f} - {latest_ob.get('low', 0):.5f}</p>
                </div>
                """, unsafe_allow_html=True)
        
        with col2:
            if smc_features['liquidity_zones']:
                latest_liq = smc_features['liquidity_zones'][-1]
                liq_type = latest_liq.get('type', 'liquidity')
                
                st.markdown(f"""
                <div class="liquidity-card">
                    <h4>💧 Latest Liquidity</h4>
                    <p>Type: <strong>{liq_type.upper()}</strong></p>
                    <p>Level: {latest_liq.get('level', 0):.5f}</p>
                </div>
                """, unsafe_allow_html=True)
        
        vp = smc_features['volume_profile']
        if vp['poc']:
            volume_table = {
                "Metric": ["POC", "VAH", "VAL"],
                "Value": [
                    f"{vp['poc']:.5f}",
                    f"{vp.get('vah', 0):.5f}",
                    f"{vp.get('val', 0):.5f}"
                ]
            }
            st.markdown("### 🎯 Volume Profile", unsafe_allow_html=True)
            col1_, col2_, col3_ = st.columns([1, 2, 1])
            with col2_:
                st.table(pd.DataFrame(volume_table))
        
        # Latest signal alert
        if smc_features['signals']:
            latest_signal = smc_features['signals'][-1]
            signal_color = "#00ff88" if latest_signal['type'] == 'buy' else "#ff4757"
            
            st.markdown(f"""
            <div class="signal-alert">
                <h3>⚡ LATEST SIGNAL: {latest_signal['type'].upper()}</h3>
                <p>Price: {latest_signal.get('price', 0):.5f} | Strength: {latest_signal.get('strength', 0):.1f}</p>
                <p>Time: {latest_signal.get('timestamp', 'N/A')}</p>
            </div>
            """, unsafe_allow_html=True)
        
        # Create the ULTIMATE chart
        st.markdown("### 📊 Ultimate SMC Analysis Chart")
        
        # Filter features based on toggles
        filtered_features = smc_features.copy()
        if not show_order_blocks:
            filtered_features['order_blocks'] = []
        if not show_liquidity:
            filtered_features['liquidity_zones'] = []
        if not show_supply_demand:
            filtered_features['supply_demand_zones'] = {'supply': [], 'demand': []}
        if not show_fvg:
            filtered_features['fair_value_gaps'] = []
        if not show_structure:
            filtered_features['bos_choch_points'] = {'bos': [], 'choch': []}
        if not show_pivots:
            filtered_features['pivot_points'] = {'highs': [], 'lows': []}
        if not show_volume_profile:
            filtered_features['volume_profile'] = {'poc': None, 'vah': None, 'val': None}
        if not show_harmonics:
            filtered_features['harmonic_patterns'] = []
        if not show_wyckoff:
            filtered_features['wyckoff_analysis'] = {'phase': 'Unknown', 'events': [], 
                                                     'accumulation_zones': [], 'distribution_zones': []}
        if not show_signals:
            filtered_features['signals'] = []
        
        # Generate chart
        chart = chart_gen.create_ultimate_smc_chart(
            df, 
            filtered_features,
            selected_pair,
            config.timeframe_map.get(selected_tf, selected_tf)
        )
        
        st.plotly_chart(chart, use_container_width=True)
        
        # Detailed analysis sections
        with st.expander("📊 Detailed SMC Analysis", expanded=False):
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("#### 📦 Order Blocks Analysis")
                if smc_features['order_blocks']:
                    ob_df = pd.DataFrame(smc_features['order_blocks'][-10:])
                    st.dataframe(ob_df, use_container_width=True)
                else:
                    st.info("No order blocks detected")
                
                st.markdown("#### 💧 Liquidity Zones")
                if smc_features['liquidity_zones']:
                    liq_df = pd.DataFrame(smc_features['liquidity_zones'][-10:])
                    st.dataframe(liq_df, use_container_width=True)
                else:
                    st.info("No liquidity zones detected")
            
            with col2:
                st.markdown("#### 🎯 Fair Value Gaps")
                if smc_features['fair_value_gaps']:
                    fvg_df = pd.DataFrame(smc_features['fair_value_gaps'][-10:])
                    st.dataframe(fvg_df, use_container_width=True)
                else:
                    st.info("No FVGs detected")
                
                st.markdown("#### 📊 Market Structure")
                st.json(smc_features['market_structure'])
        
        # Data preview
        with st.expander("📋 Raw Data Preview (Latest First)", expanded=False):
            # Show comprehensive data columns
            st.markdown(f"**Available Indicators:** {', '.join(df.columns.tolist())}")
            
            # Display latest data
            display_df = df.iloc[::-1].head(50)  # Reverse for latest first
            st.dataframe(display_df, use_container_width=True, height=400)
        
        # Summary JSON preview
        if summary:
            with st.expander("🔍 Complete Analysis Summary", expanded=False):
                st.json(summary)
        
        # Export section
        st.markdown("### 💾 Export Options")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("📊 Export Chart as HTML", key="export_chart"):
                html_str = chart.to_html(include_plotlyjs='cdn')
                st.download_button(
                    label="Download Chart HTML",
                    data=html_str,
                    file_name=f"{selected_pair}_{selected_tf}_smc_chart.html",
                    mime="text/html"
                )
        
        with col2:
            if st.button("📋 Export Analysis Report", key="export_analysis"):
                analysis_report = {
                    "pair": selected_pair,
                    "timeframe": selected_tf,
                    "timestamp": datetime.now().isoformat(),
                    "bars_analyzed": len(df),
                    "latest_price": float(df['close'].iloc[-1]),
                    "smc_features": {
                        "order_blocks": len(smc_features['order_blocks']),
                        "liquidity_zones": len(smc_features['liquidity_zones']),
                        "fair_value_gaps": len(smc_features['fair_value_gaps']),
                        "signals": len(smc_features['signals'])
                    },
                    "market_structure": smc_features['market_structure'],
                    "wyckoff_phase": smc_features['wyckoff_analysis']['phase'],
                    "volume_profile": smc_features['volume_profile']
                }
                
                st.download_button(
                    label="Download Analysis JSON",
                    data=json.dumps(analysis_report, indent=2),
                    file_name=f"{selected_pair}_{selected_tf}_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json"
                )
        
        with col3:
            if st.button("📊 Export Filtered Data", key="export_data"):
                export_df = df.copy()
                export_df.index = export_df.index.strftime('%Y-%m-%d %H:%M:%S')
                
                csv_data = export_df.to_csv()
                st.download_button(
                    label="Download CSV Data",
                    data=csv_data,
                    file_name=f"{selected_pair}_{selected_tf}_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )
        
        # Performance metrics
        st.markdown("### 📈 Performance Metrics")
        
        if len(df) > 0:
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                # Calculate returns
                returns = df['close'].pct_change().dropna()
                sharpe = (returns.mean() / returns.std() * np.sqrt(252)) if returns.std() != 0 else 0
                st.metric("Sharpe Ratio", f"{sharpe:.2f}")
            
            with col2:
                # Max drawdown
                cumret = (1 + returns).cumprod()
                running_max = cumret.expanding().max()
                drawdown = (cumret - running_max) / running_max
                max_dd = drawdown.min()
                st.metric("Max Drawdown", f"{max_dd:.2%}")
            
            with col3:
                # Win rate from signals
                if smc_features['signals']:
                    # Simple win rate calculation
                    wins = sum(1 for i, s in enumerate(smc_features['signals'][:-1]) 
                              if s['type'] == 'buy' and df['close'].iloc[-1] > s.get('price', 0))
                    win_rate = (wins / len(smc_features['signals']) * 100) if smc_features['signals'] else 0
                    st.metric("Signal Win Rate", f"{win_rate:.1f}%")
                else:
                    st.metric("Signal Win Rate", "N/A")
            
            with col4:
                # Volatility
                volatility = returns.std() * np.sqrt(252) * 100
                st.metric("Annual Volatility", f"{volatility:.1f}%")
        
        # Footer with refresh option
        st.markdown("---")
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col2:
            if st.button("🔄 Refresh Data", key="refresh_data", use_container_width=True):
                st.rerun()
        
        # About section
        with st.expander("ℹ️ About ncOS Ultimate SMC Dashboard", expanded=False):
            st.markdown("""
            ### 🎯 Features
            - **Complete SMC Analysis**: Order Blocks, Liquidity Zones, FVG, Supply/Demand
            - **Market Structure**: BOS/CHoCH detection, Pivot Points
            - **Volume Profile**: POC, VAH, VAL visualization
            - **Harmonic Patterns**: Advanced pattern recognition
            - **Wyckoff Analysis**: Accumulation/Distribution phases
            - **Trading Signals**: Entry/Exit points with strength indicators
            
            ### 📊 Data Processing
            - Reads COMPREHENSIVE CSV files with all technical indicators
            - Parses SUMMARY JSON files for complete analysis
            - Configurable bar limits for performance
            - Real-time feature toggling
            
            ### 🚀 Performance
            - Optimized for large datasets
            - Efficient memory usage
            - Fast chart rendering
            """)

if __name__ == "__main__":
    main()
