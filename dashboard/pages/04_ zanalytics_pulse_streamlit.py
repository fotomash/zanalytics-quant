import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time

# Page configuration
st.set_page_config(
    page_title="Zanalytics Pulse | The Whisperer",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for sophisticated styling
st.markdown(
    """
<style>
    /* Dark theme with professional aesthetics */
    .stApp {
        background: linear-gradient(135deg, #0B1220 0%, #111827 100%);
    }
    
    /* Custom metric cards */
    .metric-card {
        background: rgba(31, 41, 55, 0.5);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(75, 85, 99, 0.3);
        border-radius: 12px;
        padding: 20px;
        margin: 10px 0;
    }
    
    .discipline-high { color: #22C55E; }
    .discipline-medium { color: #FBBF24; }
    .discipline-low { color: #EF4444; }
    
    /* Whisperer feed styling */
    .whisper-message {
        background: rgba(31, 41, 55, 0.3);
        border-left: 3px solid;
        padding: 12px;
        margin: 8px 0;
        border-radius: 0 8px 8px 0;
    }
    
    .whisper-insight { border-color: #3B82F6; }
    .whisper-warning { border-color: #FBBF24; }
    .whisper-success { border-color: #22C55E; }
    .whisper-alert { border-color: #EF4444; }
    
    /* Professional headers */
    h1, h2, h3 {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        font-weight: 600;
    }
    
    /* Metric emphasis */
    .big-metric {
        font-size: 2.5rem;
        font-weight: 700;
        line-height: 1;
    }
    
    .metric-label {
        font-size: 0.875rem;
        color: #9CA3AF;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
</style>
""",
    unsafe_allow_html=True,
)

# Initialize session state
if 'discipline_score' not in st.session_state:
    st.session_state.discipline_score = 85
    st.session_state.patience_index = 72
    st.session_state.conviction_rate = 68
    st.session_state.profit_efficiency = 74
    st.session_state.current_pnl = 248.00
    st.session_state.session_equity = 203229.05
    st.session_state.whispers = []

# Simulated real-time data
def get_market_data():
    return {
        'vix': 14.82 + np.random.randn() * 0.5,
        'dxy': 103.45 + np.random.randn() * 0.2,
        'regime': np.random.choice(['Risk-On', 'Neutral', 'Risk-Off'], p=[0.3, 0.5, 0.2])
    }

def calculate_discipline_events():
    """Generate discipline-impacting events for the session"""
    events = [
        {'time': '09:30', 'type': 'positive', 'impact': +5, 'description': 'Followed pre-market checklist'},
        {'time': '10:15', 'type': 'negative', 'impact': -8, 'description': 'Oversized position on B-setup'},
        {'time': '11:00', 'type': 'positive', 'impact': +3, 'description': 'Respected cooling-off period'},
        {'time': '14:30', 'type': 'negative', 'impact': -12, 'description': 'Potential revenge trade detected'},
        {'time': '15:45', 'type': 'positive', 'impact': +7, 'description': 'Protected profits at target'}
    ]
    return events

def generate_session_trajectory():
    """Generate session P&L trajectory with behavioral markers"""
    hours = pd.date_range(start='2025-01-01 09:30', end='2025-01-01 16:00', freq='15min')
    base_pnl = np.cumsum(np.random.randn(len(hours)) * 50)
    
    # Add behavioral impact points
    behavioral_events = [
        {'time': 10, 'type': 'revenge', 'impact': -150},
        {'time': 20, 'type': 'overconfidence', 'impact': -80},
        {'time': 35, 'type': 'milestone', 'impact': 200}
    ]
    
    for event in behavioral_events:
        if event['time'] < len(base_pnl):
            base_pnl[event['time']:] += event['impact']
    
    return pd.DataFrame({
        'time': hours,
        'pnl': base_pnl,
        'events': ['revenge' if i == 10 else 'overconfidence' if i == 20 else 'milestone' if i == 35 else None 
                   for i in range(len(hours))]
    })

# Header Section
st.markdown("# 🧭 Zanalytics Pulse")
st.markdown("### Your Behavioral Trading Co-Pilot")

# Market Context Bar
market_data = get_market_data()
col1, col2, col3, col4 = st.columns([1, 1, 1, 2])

with col1:
    st.metric("VIX", f"{market_data['vix']:.2f}", 
              f"{np.random.choice(['+', '-'])}{abs(np.random.randn()*0.5):.2f}")

with col2:
    st.metric("DXY", f"{market_data['dxy']:.2f}",
              f"{np.random.choice(['+', '-'])}{abs(np.random.randn()*0.2):.2f}")

with col3:
    regime_color = {'Risk-On': '🟢', 'Neutral': '🟡', 'Risk-Off': '🔴'}
    st.metric("Regime", f"{regime_color[market_data['regime']]} {market_data['regime']}")

with col4:
    st.metric("System Status", "✅ All Systems Operational", "Lag: ~2ms")

st.divider()

# Main Dashboard Layout
col_left, col_center, col_right = st.columns([1.5, 2, 1.5])

# LEFT COLUMN - Behavioral Compass
with col_left:
    st.markdown("### 🎯 Behavioral Compass")
    
    # Create the donut chart for behavioral metrics
    fig = go.Figure()
    
    # Behavioral metrics with colors
    metrics = [
        {'name': 'Discipline', 'value': st.session_state.discipline_score, 'color': '#22C55E'},
        {'name': 'Patience', 'value': st.session_state.patience_index, 'color': '#3B82F6'},
        {'name': 'Efficiency', 'value': st.session_state.profit_efficiency, 'color': '#06B6D4'},
        {'name': 'Conviction', 'value': st.session_state.conviction_rate, 'color': '#8B5CF6'}
    ]
    
    # Create concentric donut rings
    for i, metric in enumerate(metrics):
        fig.add_trace(go.Pie(
            values=[metric['value'], 100-metric['value']],
            labels=[metric['name'], ''],
            hole=0.4 + i*0.1,
            marker=dict(colors=[metric['color'], 'rgba(31, 41, 55, 0.3)']),
            textinfo='none',
            hovertemplate=f"{metric['name']}: {metric['value']}%<extra></extra>",
            showlegend=False,
            domain=dict(x=[0.1*i, 1-0.1*i], y=[0.1*i, 1-0.1*i])
        ))
    
    # Add center text
    fig.add_annotation(
        text=f"<b>{int(np.mean([m['value'] for m in metrics]))}%</b><br>Overall",
        x=0.5, y=0.5,
        font=dict(size=20, color='white'),
        showarrow=False
    )
    
    fig.update_layout(
        height=300,
        margin=dict(t=0, b=0, l=0, r=0),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Behavioral Metrics Details
    for metric in metrics:
        col_m1, col_m2 = st.columns([3, 1])
        with col_m1:
            st.markdown(f"**{metric['name']}**")
        with col_m2:
            color = metric['color']
            st.markdown(f"<span style='color: {color}; font-weight: bold;'>{metric['value']}%</span>", 
                       unsafe_allow_html=True)
    
    st.divider()
    
    # Pattern Watch
    st.markdown("### 🎯 Pattern Watch")
    
    patterns = [
        {'name': 'Revenge Trading', 'status': 'OK', 'color': '#22C55E'},
        {'name': 'FOMO', 'status': 'OK', 'color': '#22C55E'},
        {'name': 'Fear (Cut Winners)', 'status': 'ALERT', 'color': '#FBBF24'},
        {'name': 'Overconfidence', 'status': 'OK', 'color': '#22C55E'}
    ]
    
    for pattern in patterns:
        st.markdown(
            f"<div style='padding: 8px; margin: 4px 0; background: rgba(31,41,55,0.3); "
            f"border-left: 3px solid {pattern['color']}; border-radius: 0 6px 6px 0;'>"
            f"<span style='color: #9CA3AF;'>{pattern['name']}:</span> "
            f"<span style='color: {pattern['color']}; font-weight: bold;'>{pattern['status']}</span>"
            f"</div>",
            unsafe_allow_html=True
        )

# CENTER COLUMN - Session Vitals & Trajectory
with col_center:
    # Session Vitals
    st.markdown("### 💰 Session Vitals")
    
    vital_cols = st.columns(3)
    with vital_cols[0]:
        pnl_color = '#22C55E' if st.session_state.current_pnl >= 0 else '#EF4444'
        st.markdown(
            f"<div class='metric-card'>"
            f"<div class='metric-label'>P&L</div>"
            f"<div class='big-metric' style='color: {pnl_color};'>"
            f"${st.session_state.current_pnl:+.2f}</div>"
            f"</div>",
            unsafe_allow_html=True
        )
    
    with vital_cols[1]:
        st.markdown(
            f"<div class='metric-card'>"
            f"<div class='metric-label'>Equity</div>"
            f"<div class='big-metric'>${st.session_state.session_equity:,.0f}</div>"
            f"</div>",
            unsafe_allow_html=True
        )
    
    with vital_cols[2]:
        target_progress = min((st.session_state.current_pnl / 2000) * 100, 100)
        st.markdown(
            f"<div class='metric-card'>"
            f"<div class='metric-label'>Target Progress</div>"
            f"<div class='big-metric'>{target_progress:.0f}%</div>"
            f"</div>",
            unsafe_allow_html=True
        )
    
    # Session Trajectory Chart
    st.markdown("### 📈 Session Trajectory")
    
    trajectory_data = generate_session_trajectory()
    
    fig_trajectory = go.Figure()
    
    # Add P&L line
    fig_trajectory.add_trace(go.Scatter(
        x=trajectory_data['time'],
        y=trajectory_data['pnl'],
        mode='lines',
        name='P&L',
        line=dict(color='#22C55E', width=2),
        fill='tozeroy',
        fillcolor='rgba(34, 197, 94, 0.1)'
    ))
    
    # Add behavioral event markers
    event_colors = {
        'revenge': '#EF4444',
        'overconfidence': '#FBBF24', 
        'milestone': '#22C55E'
    }
    
    for event_type, color in event_colors.items():
        event_data = trajectory_data[trajectory_data['events'] == event_type]
        if not event_data.empty:
            fig_trajectory.add_trace(go.Scatter(
                x=event_data['time'],
                y=event_data['pnl'],
                mode='markers',
                name=event_type.capitalize(),
                marker=dict(size=12, color=color, symbol='circle'),
                hovertemplate=f'{event_type.capitalize()} Event<br>P&L: %{{y:.2f}}<extra></extra>'
            ))
    
    # Add zero line
    fig_trajectory.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.3)
    
    fig_trajectory.update_layout(
        height=300,
        margin=dict(t=0, b=20, l=0, r=0),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(
            showgrid=False,
            color='#9CA3AF',
            tickformat='%H:%M'
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor='rgba(75, 85, 99, 0.2)',
            color='#9CA3AF',
            title='P&L ($)'
        ),
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            bgcolor='rgba(0,0,0,0)',
            font=dict(color='#9CA3AF', size=10)
        ),
        hovermode='x unified'
    )
    
    st.plotly_chart(fig_trajectory, use_container_width=True)
    
    # Discipline Posture
    st.markdown("### 📊 Discipline Posture")
    
    # Generate discipline data for last 10 trades
    discipline_history = [78, 82, 75, 88, 92, 85, 79, 83, 87, st.session_state.discipline_score]
    
    fig_discipline = go.Figure()
    
    colors = ['#22C55E' if d > 80 else '#FBBF24' if d > 60 else '#EF4444' for d in discipline_history]
    
    fig_discipline.add_trace(go.Bar(
        x=list(range(1, 11)),
        y=discipline_history,
        marker_color=colors,
        text=[f'{d}%' for d in discipline_history],
        textposition='outside',
        textfont=dict(color='#9CA3AF', size=10),
        hovertemplate='Trade %{x}<br>Discipline: %{y}%<extra></extra>'
    ))
    
    fig_discipline.update_layout(
        height=200,
        margin=dict(t=20, b=20, l=0, r=0),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(
            title='Last 10 Trades',
            color='#9CA3AF',
            showgrid=False
        ),
        yaxis=dict(
            range=[0, 100],
            showgrid=True,
            gridcolor='rgba(75, 85, 99, 0.2)',
            color='#9CA3AF'
        ),
        showlegend=False
    )
    
    st.plotly_chart(fig_discipline, use_container_width=True)

# RIGHT COLUMN - The Whisperer
with col_right:
    st.markdown("### 🤖 The Whisperer")
    
    # Generate whispers
    whispers = [
        {
            'time': '09:30:00',
            'type': 'insight',
            'message': 'Good morning. Market regime: Neutral. Your win rate in these conditions: 68%'
        },
        {
            'time': '10:15:23',
            'type': 'warning',
            'message': 'Position size exceeds plan for B-setup. Discipline Score impacted (-8 pts)'
        },
        {
            'time': '11:00:45',
            'type': 'success',
            'message': 'Well done respecting the cooling-off period. Pattern recognition improving.'
        },
        {
            'time': '14:30:12',
            'type': 'alert',
            'message': 'Potential revenge trade detected. Your win rate after losses: 42%. Consider stepping back.'
        },
        {
            'time': '15:45:00',
            'type': 'success',
            'message': '🎯 Profit target reached! Consider protecting gains. Your efficiency score: 74%'
        }
    ]
    
    # Whisper feed container (scrollable)
    whisper_container = st.container()
    with whisper_container:
        type_icons = {'insight': '💡', 'warning': '⚠️', 'success': '✅', 'alert': '🚨'}
        html = ["<div style='max-height:400px; overflow:auto'>"]
        for w in whispers:
            icon = type_icons.get(w['type'], '💬')
            html.append(
                f"<div class='whisper-message whisper-{w['type']}'>"
                f"<div style='display:flex;align-items:start;'>"
                f"<span style='font-size:1.2em;margin-right:8px'>{icon}</span>"
                f"<div style='flex:1'>"
                f"<div style='color:#6B7280;font-size:0.75em'>{w['time']}</div>"
                f"<div style='color:#E5E7EB;margin-top:4px'>{w['message']}</div>"
                f"</div></div></div>"
            )
        html.append("</div>")
        st.markdown("\n".join(html), unsafe_allow_html=True)
    
    # Action buttons
    st.markdown("### Quick Actions")
    
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("📝 Add Note", use_container_width=True):
            st.info("Journal entry added")
    
    with col_btn2:
        if st.button("🔒 Protect Profits", use_container_width=True):
            st.success("Stop-loss moved to breakeven")
    
    if st.button("💬 Open Full Conversation →", use_container_width=True, type="primary"):
        st.info("Opening Telegram conversation...")

# Bottom Section - Additional Insights
st.divider()

bottom_cols = st.columns(4)

with bottom_cols[0]:
    st.markdown("### Trade Quality")
    quality_data = pd.DataFrame({
        'Setup': ['A+', 'B', 'C'],
        'Count': [12, 8, 3],
        'Win Rate': [75, 50, 33]
    })
    
    fig_quality = go.Figure(go.Bar(
        x=quality_data['Setup'],
        y=quality_data['Count'],
        marker_color=['#22C55E', '#FBBF24', '#EF4444'],
        text=quality_data['Count'],
        textposition='outside'
    ))
    
    fig_quality.update_layout(
        height=150,
        margin=dict(t=0, b=0, l=0, r=0),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(color='#9CA3AF'),
        yaxis=dict(visible=False),
        showlegend=False
    )
    
    st.plotly_chart(fig_quality, use_container_width=True)

with bottom_cols[1]:
    st.markdown("### Profit Efficiency")
    st.metric("Captured vs Potential", "74%", "+5%")
    st.progress(0.74)
    st.caption("Letting winners run better")

with bottom_cols[2]:
    st.markdown("### Risk Management")
    st.metric("Avg Risk/Trade", "1.2R")
    st.metric("Max Exposure", "3.5%", "-0.5%")

with bottom_cols[3]:
    st.markdown("### Session Momentum")
    momentum = 68
    st.metric("Positive Momentum", f"{momentum}%")
    st.progress(momentum/100)
    st.caption("Maintaining discipline")

# Auto-refresh simulation
placeholder = st.empty()
if st.button("🔄 Enable Live Updates"):
    while True:
        with placeholder.container():
            st.info("Dashboard updating...")
        time.sleep(5)
        st.rerun()
