import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from dashboard_integration import ZanflowDataConnector
from strategy_integration import StrategyManager

st.set_page_config(page_title="Strategy Signals", layout="wide")

# Initialize
@st.cache_resource
def get_connector():
    return ZanflowDataConnector()

@st.cache_resource  
def get_strategy_manager():
    return StrategyManager()

connector = get_connector()
manager = get_strategy_manager()

st.title("🎯 ZANFLOW Strategy Signals")

# Sidebar controls
with st.sidebar:
    st.header("Strategy Controls")

    # Symbol filter
    all_symbols = connector.get_all_symbols()
    selected_symbols = st.multiselect(
        "Filter Symbols",
        all_symbols,
        default=all_symbols[:5] if all_symbols else []
    )

    # Time filter
    time_filter = st.select_slider(
        "Show signals from",
        options=["1 hour", "4 hours", "24 hours", "All"],
        value="4 hours"
    )

    # Signal strength filter
    strength_filter = st.multiselect(
        "Signal Strength",
        ["STRONG", "MEDIUM", "SCALP"],
        default=["STRONG", "MEDIUM", "SCALP"]
    )

    # Auto-refresh
    auto_refresh = st.checkbox("Auto-refresh (5s)", value=True)

    if st.button("Clear Old Signals"):
        manager.clear_old_signals(24)
        st.success("Cleared signals older than 24 hours")

# Main content
tab1, tab2, tab3 = st.tabs(["📊 Live Signals", "📈 Performance", "⚙️ Strategy Config"])

with tab1:
    # Get signals
    all_signals = []
    for symbol in selected_symbols:
        signals = manager.get_all_signals(symbol)
        all_signals.extend(signals)

    # Filter by time
    if time_filter != "All":
        hours = int(time_filter.split()[0])
        cutoff = datetime.now() - timedelta(hours=hours)
        all_signals = [s for s in all_signals if datetime.fromisoformat(s['timestamp']) > cutoff]

    # Filter by strength
    all_signals = [s for s in all_signals if s['signal'].get('strength', 'MEDIUM') in strength_filter]

    # Sort by timestamp
    all_signals.sort(key=lambda x: x['timestamp'], reverse=True)

    # Display signals
    if all_signals:
        for signal in all_signals[:20]:  # Show last 20
            sig = signal['signal']

            # Signal card
            with st.container():
                col1, col2, col3, col4 = st.columns([1, 2, 3, 2])

                # Signal type with color
                with col1:
                    if sig['action'] == 'BUY':
                        st.success(f"🔼 {sig['action']}")
                    else:
                        st.error(f"🔽 {sig['action']}")

                # Symbol and strategy
                with col2:
                    st.write(f"**{signal['symbol']}**")
                    st.caption(signal['strategy'])

                # Reason
                with col3:
                    st.write(sig['reason'])
                    if 'target_pips' in sig:
                        st.caption(f"TP: {sig['target_pips']} pips, SL: {sig['stop_pips']} pips")

                # Timestamp
                with col4:
                    time_ago = datetime.now() - datetime.fromisoformat(signal['timestamp'])
                    if time_ago.seconds < 60:
                        st.write(f"🔴 {time_ago.seconds}s ago")
                    elif time_ago.seconds < 3600:
                        st.write(f"🟡 {time_ago.seconds // 60}m ago")
                    else:
                        st.write(f"⚪ {time_ago.seconds // 3600}h ago")

                st.divider()
    else:
        st.info("No signals matching your filters")

with tab2:
    st.header("Strategy Performance")

    # Calculate performance metrics
    if all_signals:
        df = pd.DataFrame(all_signals)

        # Signals by strategy
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Signals by Strategy")
            strategy_counts = df.groupby('strategy').size()
            st.bar_chart(strategy_counts)

        with col2:
            st.subheader("Signals by Symbol")
            symbol_counts = df.groupby('symbol').size()
            st.bar_chart(symbol_counts)

        # Signal distribution over time
        st.subheader("Signal Distribution")
        df['hour'] = pd.to_datetime(df['timestamp']).dt.hour
        hourly_dist = df.groupby('hour').size()
        st.line_chart(hourly_dist)

with tab3:
    st.header("Strategy Configuration")

    # Strategy settings
    st.subheader("RSI Momentum Strategy")
    col1, col2 = st.columns(2)
    with col1:
        rsi_oversold = st.slider("RSI Oversold", 10, 40, 30)
        rsi_overbought = st.slider("RSI Overbought", 60, 90, 70)
    with col2:
        momentum_threshold = st.slider("Momentum %", 0.0, 5.0, 1.0)

    st.subheader("Volume Breakout Strategy")
    volume_spike = st.slider("Volume Spike Multiplier", 1.5, 4.0, 2.0)

    st.subheader("Scalping Strategy")
    col1, col2 = st.columns(2)
    with col1:
        scalp_tp = st.number_input("Target Pips", 3, 20, 5)
    with col2:
        scalp_sl = st.number_input("Stop Loss Pips", 2, 10, 3)

    if st.button("Save Configuration"):
        st.success("Configuration saved!")

# Auto-refresh
if auto_refresh:
    time.sleep(5)
    st.rerun()
