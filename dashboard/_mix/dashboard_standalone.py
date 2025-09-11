
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import json
import os
from datetime import datetime, timedelta
import numpy as np
import glob

# Page config
st.set_page_config(
    page_title="ZANALYTICS - Real Data Intelligence",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #1e3c72 0%, #2a5298 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: white;
        padding: 1rem;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        border-left: 4px solid #2a5298;
    }
    .status-online { color: #28a745; }
    .status-offline { color: #dc3545; }
    .status-warning { color: #ffc107; }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown("""
<div class="main-header">
    <h1>🚀 ZANALYTICS INTELLIGENCE DASHBOARD</h1>
    <p>Real-Time Trading Data Intelligence & Local File Analysis</p>
</div>
""", unsafe_allow_html=True)

# Load local data function
@st.cache_data
def load_local_data():
    """Load all available local data files"""
    data_files = {
        'tick_data': [],
        'bar_data': [],
        'json_analysis': [],
        'csv_files': []
    }
    
    # Search for data files in current directory
    file_patterns = [
        '*.csv',
        '*.json',
        'data/*.csv',
        'exports/*.csv',
        'uploads/*.csv'
    ]
    
    all_files = []
    for pattern in file_patterns:
        all_files.extend(glob.glob(pattern))
    
    for file_path in all_files:
        if not os.path.exists(file_path):
            continue
            
        file_name = os.path.basename(file_path)
        file_size = os.path.getsize(file_path)
        file_mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
        
        if file_name.endswith('.json'):
            data_files['json_analysis'].append({
                'name': file_name,
                'path': file_path,
                'size': file_size,
                'modified': file_mtime
            })
        elif file_name.endswith('.csv'):
            data_files['csv_files'].append({
                'name': file_name,
                'path': file_path,
                'size': file_size,
                'modified': file_mtime
            })
            
            # Classify CSV files
            if 'TICK' in file_name.upper():
                data_files['tick_data'].append({
                    'name': file_name,
                    'path': file_path,
                    'size': file_size,
                    'modified': file_mtime
                })
            elif any(tf in file_name.upper() for tf in ['M1', 'M5', 'M15', 'M30', 'H1', 'H4', 'D1']):
                data_files['bar_data'].append({
                    'name': file_name,
                    'path': file_path,
                    'size': file_size,
                    'modified': file_mtime
                })
    
    return data_files

# Load CSV data
@st.cache_data
def load_csv_data(file_path, max_rows=10000):
    """Load CSV data with automatic delimiter detection"""
    try:
        # Try tab-separated first (your exports)
        df = pd.read_csv(file_path, sep='\t', nrows=max_rows)
        if len(df.columns) == 1:
            # Try comma-separated
            df = pd.read_csv(file_path, sep=',', nrows=max_rows)
        
        # Parse timestamp column if it exists
        timestamp_cols = ['timestamp', 'time', 'datetime', 'date']
        for col in timestamp_cols:
            if col in df.columns:
                try:
                    df[col] = pd.to_datetime(df[col])
                    df = df.set_index(col)
                    break
                except:
                    pass
        
        return df
    except Exception as e:
        st.error(f"Error loading {file_path}: {str(e)}")
        return None

# Load JSON analysis
@st.cache_data
def load_json_analysis(file_path):
    """Load JSON analysis file"""
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        st.error(f"Error loading {file_path}: {str(e)}")
        return None

# Main dashboard
def main():
    # Load data
    data_files = load_local_data()
    
    # Sidebar
    st.sidebar.title("📊 Data Controls")
    
    # System Status
    st.sidebar.markdown("### 🔴 System Status")
    total_files = len(data_files['csv_files']) + len(data_files['json_analysis'])
    
    if total_files > 0:
        st.sidebar.markdown('<span class="status-online">✅ LOCAL DATA ACTIVE</span>', unsafe_allow_html=True)
        st.sidebar.metric("Total Files", total_files)
        st.sidebar.metric("CSV Files", len(data_files['csv_files']))
        st.sidebar.metric("JSON Analysis", len(data_files['json_analysis']))
        st.sidebar.metric("Tick Data Files", len(data_files['tick_data']))
        st.sidebar.metric("Bar Data Files", len(data_files['bar_data']))
    else:
        st.sidebar.markdown('<span class="status-offline">❌ NO DATA FOUND</span>', unsafe_allow_html=True)
        st.sidebar.warning("No data files found. Please check your file locations.")
    
    # File selection
    if data_files['csv_files']:
        st.sidebar.markdown("### 📁 Select Data File")
        selected_file = st.sidebar.selectbox(
            "Choose CSV file:",
            options=[f['name'] for f in data_files['csv_files']],
            key="csv_selector"
        )
        
        if selected_file:
            # Find selected file path
            file_info = next((f for f in data_files['csv_files'] if f['name'] == selected_file), None)
            
            if file_info:
                # Display file info
                st.sidebar.markdown(f"**File:** {file_info['name']}")
                st.sidebar.markdown(f"**Size:** {file_info['size']:,} bytes")
                st.sidebar.markdown(f"**Modified:** {file_info['modified'].strftime('%Y-%m-%d %H:%M:%S')}")
                
                # Load and display data
                df = load_csv_data(file_info['path'])
                
                if df is not None:
                    # Main content area
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        st.metric("Total Records", len(df), f"+{len(df):,}")
                    with col2:
                        st.metric("Columns", len(df.columns))
                    with col3:
                        if 'bid' in df.columns and 'ask' in df.columns:
                            avg_spread = (df['ask'] - df['bid']).mean() if len(df) > 0 else 0
                            st.metric("Avg Spread", f"{avg_spread:.2f}")
                        elif 'close' in df.columns:
                            current_price = df['close'].iloc[-1] if len(df) > 0 else 0
                            st.metric("Last Price", f"{current_price:.2f}")
                        else:
                            st.metric("Data Type", "Unknown")
                    with col4:
                        if len(df) > 1:
                            time_span = df.index[-1] - df.index[0] if hasattr(df.index, 'dtype') and 'datetime' in str(df.index.dtype) else "N/A"
                            st.metric("Time Span", str(time_span).split('.')[0] if time_span != "N/A" else "N/A")
                        else:
                            st.metric("Time Span", "N/A")
                    
                    # Data preview
                    st.subheader("📋 Data Preview")
                    st.dataframe(df.head(20), use_container_width=True)
                    
                    # Price chart if OHLC data available
                    if all(col in df.columns for col in ['open', 'high', 'low', 'close']):
                        st.subheader("📈 OHLC Chart")
                        
                        fig = go.Figure(data=go.Candlestick(
                            x=df.index,
                            open=df['open'],
                            high=df['high'],
                            low=df['low'],
                            close=df['close'],
                            name="OHLC"
                        ))
                        
                        fig.update_layout(
                            title=f"{selected_file} - OHLC Chart",
                            xaxis_title="Time",
                            yaxis_title="Price",
                            height=500
                        )
                        
                        st.plotly_chart(fig, use_container_width=True)
                    
                    # Tick data chart if bid/ask available
                    elif 'bid' in df.columns and 'ask' in df.columns:
                        st.subheader("📊 Bid/Ask Chart")
                        
                        fig = go.Figure()
                        fig.add_trace(go.Scatter(
                            x=df.index,
                            y=df['bid'],
                            mode='lines',
                            name='Bid',
                            line=dict(color='red')
                        ))
                        fig.add_trace(go.Scatter(
                            x=df.index,
                            y=df['ask'],
                            mode='lines',
                            name='Ask',
                            line=dict(color='blue')
                        ))
                        
                        fig.update_layout(
                            title=f"{selected_file} - Bid/Ask Chart",
                            xaxis_title="Time",
                            yaxis_title="Price",
                            height=500
                        )
                        
                        st.plotly_chart(fig, use_container_width=True)
                    
                    # Statistics
                    st.subheader("📊 Data Statistics")
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown("**Numeric Columns:**")
                        numeric_cols = df.select_dtypes(include=[np.number]).columns
                        if len(numeric_cols) > 0:
                            st.dataframe(df[numeric_cols].describe(), use_container_width=True)
                        else:
                            st.info("No numeric columns found")
                    
                    with col2:
                        st.markdown("**Column Info:**")
                        col_info = []
                        for col in df.columns:
                            col_info.append({
                                'Column': col,
                                'Type': str(df[col].dtype),
                                'Non-Null': df[col].count(),
                                'Null': df[col].isnull().sum()
                            })
                        st.dataframe(pd.DataFrame(col_info), use_container_width=True)
    
    # JSON Analysis section
    if data_files['json_analysis']:
        st.subheader("🔬 JSON Analysis Files")
        
        for json_file in data_files['json_analysis']:
            with st.expander(f"📄 {json_file['name']} ({json_file['size']:,} bytes)"):
                json_data = load_json_analysis(json_file['path'])
                if json_data:
                    st.json(json_data)
    
    # File monitor
    st.subheader("📁 File Monitor")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("**📊 CSV Files**")
        for csv_file in data_files['csv_files'][:5]:  # Show first 5
            st.markdown(f"• {csv_file['name']} ({csv_file['size']:,} bytes)")
    
    with col2:
        st.markdown("**🔬 JSON Analysis**")
        for json_file in data_files['json_analysis'][:5]:  # Show first 5
            st.markdown(f"• {json_file['name']} ({json_file['size']:,} bytes)")
    
    with col3:
        st.markdown("**⏰ Recent Activity**")
        all_files = data_files['csv_files'] + data_files['json_analysis']
        recent_files = sorted(all_files, key=lambda x: x['modified'], reverse=True)[:5]
        for file_info in recent_files:
            time_ago = datetime.now() - file_info['modified']
            if time_ago.days > 0:
                time_str = f"{time_ago.days}d ago"
            elif time_ago.seconds > 3600:
                time_str = f"{time_ago.seconds//3600}h ago"
            elif time_ago.seconds > 60:
                time_str = f"{time_ago.seconds//60}m ago"
            else:
                time_str = "Just now"
            st.markdown(f"• {file_info['name']} ({time_str})")

if __name__ == "__main__":
    main()
