"""
Advanced Risk Management Dashboard - Scientific Visualization with Behavioral Insights
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import redis
import json
import time
import requests
from typing import Dict, List, Optional, Tuple
import os
from dotenv import load_dotenv

# Safe MT5 import
try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    MT5_AVAILABLE = False
    mt5 = None

# Load environment variables
load_dotenv()

# Page configuration
st.set_page_config(
    page_title="Zanalytics Pulse - Advanced Risk Manager",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for enhanced styling
st.markdown("""
<style>
    .risk-metric {
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
    .risk-high { background-color: #ffebee; color: #c62828; }
    .risk-medium { background-color: #fff3e0; color: #ef6c00; }
    .risk-low { background-color: #e8f5e9; color: #2e7d32; }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 1rem;
        color: white;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .pulse-tile {
        background: white;
        padding: 1rem;
        border-radius: 0.5rem;
        border: 1px solid #e0e0e0;
        margin: 0.5rem 0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .risk-slider-container {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
    }
    .psychology-insight {
        background: #e3f2fd;
        border-left: 4px solid #2196f3;
        padding: 1rem;
        margin: 1rem 0;
        border-radius: 0 0.5rem 0.5rem 0;
    }
</style>
""", unsafe_allow_html=True)

# API Configuration
DJANGO_API_URL = os.getenv("DJANGO_API_URL", "http://django:8000")

def safe_api_call(method: str, path: str, payload: Dict = None, timeout: float = 2.0) -> Dict:
    """Safe API call with error handling and fallbacks"""
    try:
        url = f"{DJANGO_API_URL}/{path.lstrip('/')}"
        
        if method.upper() == "GET":
            response = requests.get(url, timeout=timeout)
        elif method.upper() == "POST":
            response = requests.post(url, json=payload or {}, timeout=timeout)
        else:
            return {"error": f"Unsupported method: {method}"}
        
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"HTTP {response.status_code}"}
            
    except requests.exceptions.Timeout:
        return {"error": "API timeout"}
    except requests.exceptions.ConnectionError:
        return {"error": "API connection failed"}
    except Exception as e:
        return {"error": str(e)}

class AdvancedPulseRiskManager:
    """Advanced Risk Manager with Scientific Position Sizing and Behavioral Insights"""

    def __init__(self):
        # Get credentials from environment (no defaults to real values)
        self.mt5_login = os.getenv('MT5_LOGIN')
        self.mt5_password = os.getenv('MT5_PASSWORD')
        self.mt5_server = os.getenv('MT5_SERVER')
        
        # Initialize connections
        self.connected = False
        self.mt5_available = MT5_AVAILABLE
        
        # Redis connection with error handling
        try:
            self.redis_client = redis.Redis(
                host=os.getenv('REDIS_HOST', 'redis'), 
                port=int(os.getenv('REDIS_PORT', 6379)), 
                decode_responses=True,
                socket_timeout=2.0
            )
            self.redis_client.ping()
            self.redis_available = True
        except Exception:
            self.redis_available = False
            self.redis_client = None

    def connect(self) -> bool:
        """Connect to MT5 with proper error handling"""
        if not self.mt5_available:
            st.warning("⚠️ MT5 not available - running in mock mode")
            return False
        
        if not all([self.mt5_login, self.mt5_password, self.mt5_server]):
            st.warning("⚠️ MT5 credentials not configured - running in mock mode")
            return False

        try:
            if not mt5.initialize():
                return False

            authorized = mt5.login(
                login=int(self.mt5_login),
                password=self.mt5_password,
                server=self.mt5_server
            )

            if authorized:
                self.connected = True
                return True
            return False
        except Exception as e:
            st.error(f"MT5 Connection Error: {e}")
            return False

    def get_account_info(self) -> Dict:
        """Get account information with fallback"""
        if not self.connected:
            if not self.connect():
                # Return mock data for development
                return {
                    'login': 'MOCK',
                    'server': 'MOCK-SERVER',
                    'balance': 10000.00,
                    'equity': 10000.00,
                    'margin': 0.00,
                    'free_margin': 10000.00,
                    'margin_level': 0.00,
                    'profit': 0.00,
                    'leverage': 100,
                    'currency': 'USD',
                    'name': 'Mock Account',
                    'company': 'Mock Broker',
                }

        try:
            account_info = mt5.account_info()
            if account_info is None:
                return {}

            return {
                'login': account_info.login,
                'server': account_info.server,
                'balance': account_info.balance,
                'equity': account_info.equity,
                'margin': account_info.margin,
                'free_margin': account_info.margin_free,
                'margin_level': account_info.margin_level,
                'profit': account_info.profit,
                'leverage': account_info.leverage,
                'currency': account_info.currency,
                'name': account_info.name,
                'company': account_info.company,
            }
        except Exception as e:
            st.error(f"Error getting account info: {e}")
            return {}

    def get_positions(self) -> pd.DataFrame:
        """Get all open positions with error handling"""
        if not self.connected:
            return pd.DataFrame()

        try:
            positions = mt5.positions_get()
            if positions is None or len(positions) == 0:
                return pd.DataFrame()

            df = pd.DataFrame(list(positions), columns=positions[0]._asdict().keys())
            df['time'] = pd.to_datetime(df['time'], unit='s')
            df['time_update'] = pd.to_datetime(df['time_update'], unit='s')
            return df
        except Exception as e:
            st.error(f"Error getting positions: {e}")
            return pd.DataFrame()

    def get_confluence_score(self) -> Dict:
        """Get confluence score from Pulse API with fallback"""
        result = safe_api_call("POST", "score/peek", {})
        
        if "error" in result:
            # Return mock data for development
            return {
                "score": np.random.randint(60, 90),
                "grade": "High",
                "reasons": [
                    "SMC Break of Structure confirmed",
                    "Wyckoff accumulation phase detected",
                    "Volume divergence present"
                ],
                "component_scores": {
                    "smc": 85,
                    "wyckoff": 78,
                    "technical": 72
                }
            }
        
        return result

    def get_risk_summary(self) -> Dict:
        """Get risk summary from Pulse API with fallback"""
        result = safe_api_call("GET", "risk/summary")
        
        if "error" in result:
            # Return mock data
            return {
                "daily_risk_used": 15.0,
                "risk_left": 85.0,
                "trades_left": 3,
                "status": "Stable",
                "warnings": []
            }
        
        return result

    def get_top_opportunities(self, n: int = 3) -> List[Dict]:
        """Get top trading opportunities with fallback"""
        result = safe_api_call("GET", f"signals/top?n={n}")
        
        if "error" in result or not isinstance(result, list):
            # Return mock opportunities
            symbols = ['EURUSD', 'GBPUSD', 'USDJPY', 'XAUUSD']
            opportunities = []
            
            for i in range(n):
                symbol = symbols[i % len(symbols)]
                opportunities.append({
                    "symbol": symbol,
                    "score": np.random.randint(70, 95),
                    "rr": round(np.random.uniform(1.5, 3.0), 1),
                    "bias": np.random.choice(["Bull", "Bear"]),
                    "sl": f"{np.random.uniform(1.0900, 1.1100):.4f}" if symbol == "EURUSD" else "TBD",
                    "tp": f"{np.random.uniform(1.1100, 1.1300):.4f}" if symbol == "EURUSD" else "TBD",
                    "reasons": [
                        "Strong momentum detected",
                        "Key level break confirmed",
                        "Volume supporting move"
                    ]
                })
            
            return sorted(opportunities, key=lambda x: x['score'], reverse=True)
        
        return result

def create_risk_allocation_visualization(account_equity: float, 
                                       daily_risk_pct: float, 
                                       anticipated_trades: int,
                                       confluence_score: float = 75) -> go.Figure:
    """Create scientific risk allocation visualization"""
    
    # Calculate risk amounts
    daily_risk_amount = account_equity * (daily_risk_pct / 100)
    per_trade_risk = daily_risk_amount / anticipated_trades
    
    # Confidence-based adjustment
    confidence_multiplier = min(1.0, confluence_score / 100)
    adjusted_per_trade = per_trade_risk * confidence_multiplier
    
    # Create visualization
    fig = go.Figure()
    
    # Add bars for visualization
    fig.add_trace(go.Bar(
        x=['Daily Risk Budget', 'Per-Trade Risk', 'Adjusted Risk'],
        y=[daily_risk_amount, per_trade_risk, adjusted_per_trade],
        marker_color=['#1f77b4', '#ff7f0e', '#2ca02c'],
        text=[f"${daily_risk_amount:.2f}", f"${per_trade_risk:.2f}", f"${adjusted_per_trade:.2f}"],
        textposition='auto',
    ))
    
    fig.update_layout(
        title=f"Scientific Risk Allocation<br><sub>Daily Risk: {daily_risk_pct}% of ${account_equity:,.0f}</sub>",
        xaxis_title="Risk Category",
        yaxis_title="Risk Amount ($)",
        showlegend=False,
        height=400
    )
    
    return fig

def create_psychology_insights(confluence_score: float, 
                              consecutive_losses: int, 
                              trades_today: int,
                              risk_phase: str) -> List[str]:
    """Generate behavioral psychology insights"""
    
    insights = []
    
    # Confidence-based insights
    if confluence_score > 85:
        insights.append("🟢 High confidence signal - maintain discipline but avoid overconfidence")
    elif confluence_score < 40:
        insights.append("🔴 Low confidence signal - consider skipping or reducing position size")
    
    # Loss-based insights
    if consecutive_losses >= 2:
        insights.append("⚠️ Multiple consecutive losses - activate cooling off period")
    
    # Trade frequency insights
    if trades_today >= 4:
        insights.append("⚠️ High trade frequency today - watch for fatigue effects")
    
    # Risk phase insights
    phase_insights = {
        "low_equity": "🟡 Conservative phase - focus on high probability setups",
        "stable": "🟢 Stable phase - normal risk parameters apply",
        "new_high": "🟢 Growth phase - can increase position size slightly",
        "recovery": "🟡 Recovery phase - reduce risk until back to stable"
    }
    insights.append(phase_insights.get(risk_phase, "Unknown phase"))
    
    return insights

def render_risk_control_panel(account_info: Dict, risk_summary: Dict):
    """Render advanced risk control panel with scientific sliders"""
    
    st.subheader("🔬 Scientific Risk Control Panel")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### Risk Parameters")
        
        # Daily risk slider with psychological guidance
        daily_risk_pct = st.slider(
            "Daily Risk Budget (%)", 
            0.5, 5.0, 2.0, 0.1,
            help="Maximum percentage of equity to risk today"
        )
        
        # Anticipated trades slider
        anticipated_trades = st.slider(
            "Anticipated Trades Today", 
            1, 10, 3,
            help="Number of trades you plan to take today"
        )
        
        # Calculate per-trade risk
        per_trade_risk = daily_risk_pct / anticipated_trades
        st.metric("Suggested Per-Trade Risk", f"{per_trade_risk:.2f}%", 
                 f"{anticipated_trades} trades planned")
    
    with col2:
        st.markdown("#### Risk Allocation Visualization")
        
        # Create risk allocation chart
        equity = account_info.get('equity', 10000)
        fig = create_risk_allocation_visualization(
            equity, daily_risk_pct, anticipated_trades
        )
        st.plotly_chart(fig, use_container_width=True)

def render_psychology_insights_panel(confluence_data: Dict, risk_summary: Dict):
    """Render behavioral psychology insights panel"""
    
    st.subheader("🧠 Behavioral Psychology Insights")
    
    confluence_score = confluence_data.get("score", 75)
    consecutive_losses = risk_summary.get("consecutive_losses", 0)
    trades_today = risk_summary.get("trades_used", 0)
    risk_phase = risk_summary.get("risk_phase", "stable")
    
    insights = create_psychology_insights(
        confluence_score, consecutive_losses, trades_today, risk_phase
    )
    
    for insight in insights:
        st.markdown(f'<div class="psychology-insight">{insight}</div>', 
                   unsafe_allow_html=True)
    
    # Trading principles reminder
    with st.expander("📚 Trading in the Zone Principles", expanded=False):
        st.write("✅ Think in probabilities, not predictions")
        st.write("✅ Focus on process over outcomes")
        st.write("✅ Accept uncertainty as natural")
        st.write("✅ Maintain emotional discipline")
        st.write("✅ Stick to your risk management rules")

def render_pulse_tiles(pulse_manager: AdvancedPulseRiskManager):
    """Render Pulse-specific tiles with error handling"""
    st.subheader("🎯 Pulse Decision Surface")
    
    col1, col2, col3, col4 = st.columns(4)
    
    # Confluence Score Tile
    with col1:
        confluence_data = pulse_manager.get_confluence_score()
        score = confluence_data.get("score", 0)
        grade = confluence_data.get("grade", "Unknown")
        
        st.markdown(f"""
        <div class="pulse-tile">
            <h4>Confluence Score</h4>
            <h2>{score}/100</h2>
            <p>Grade: {grade}</p>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("🔍 Explain Score", key="explain_confluence"):
            with st.expander("Score Breakdown", expanded=True):
                reasons = confluence_data.get("reasons", [])
                if reasons:
                    for reason in reasons:
                        st.write(f"• {reason}")
                else:
                    st.write("No specific reasons available")
                
                # Component scores
                components = confluence_data.get("component_scores", {})
                if components:
                    st.write("**Component Analysis:**")
                    for component, comp_score in components.items():
                        st.write(f"- {component.upper()}: {comp_score}")
    
    # Market Bias Tile
    with col2:
        bias = "Bull" if score > 60 else "Bear" if score < 40 else "Neutral"
        bias_color = "🟢" if bias == "Bull" else "🔴" if bias == "Bear" else "🟡"
        
        st.markdown(f"""
        <div class="pulse-tile">
            <h4>Market Bias</h4>
            <h2>{bias_color} {bias}</h2>
            <p>Confidence: {score}%</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Risk Remaining Tile
    with col3:
        risk_data = pulse_manager.get_risk_summary()
        risk_remaining = risk_data.get("risk_left", 0)
        
        st.markdown(f"""
        <div class="pulse-tile">
            <h4>Risk Remaining</h4>
            <h2>{risk_remaining:.1f}%</h2>
            <p>Daily Budget</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Suggested R:R Tile
    with col4:
        suggested_rr = 2.0 if score > 70 else 1.5 if score > 50 else 1.2
        
        st.markdown(f"""
        <div class="pulse-tile">
            <h4>Suggested R:R</h4>
            <h2>{suggested_rr}:1</h2>
            <p>Based on Score</p>
        </div>
        """, unsafe_allow_html=True)

def render_opportunities(pulse_manager: AdvancedPulseRiskManager):
    """Render top trading opportunities with error handling"""
    st.subheader("🎯 Top Trading Opportunities")
    
    try:
        opportunities = pulse_manager.get_top_opportunities(3)
        
        for opp in opportunities:
            with st.container():
                col1, col2, col3 = st.columns([2, 1, 1])
                
                with col1:
                    st.write(f"**{opp['symbol']}** - Score: {opp['score']}")
                    st.write(f"Bias: {opp.get('bias', 'Neutral')}")
                
                with col2:
                    st.write(f"R:R: {opp.get('rr', '—')}")
                    st.write(f"SL: {opp.get('sl', '—')}")
                
                with col3:
                    st.write(f"TP: {opp.get('tp', '—')}")
                    
                    if st.button(f"Analyze {opp['symbol']}", key=f"analyze_{opp['symbol']}"):
                        st.info(f"Opening analysis for {opp['symbol']}...")
                
                # Expandable reasons
                with st.expander("📋 Analysis Details"):
                    reasons = opp.get("reasons", [])
                    if reasons:
                        for reason in reasons:
                            st.write(f"• {reason}")
                    else:
                        st.write("No specific analysis available")
            
            st.divider()
    
    except Exception as e:
        st.error(f"Unable to load opportunities: {str(e)}")

def render_behavioral_insights(pulse_manager: AdvancedPulseRiskManager):
    """Render behavioral trading insights"""
    st.subheader("🧠 Behavioral Insights")
    
    try:
        risk_data = pulse_manager.get_risk_summary()
        warnings = risk_data.get("warnings", [])
        
        if warnings:
            st.warning("**Active Behavioral Alerts:**")
            for warning in warnings:
                st.write(f"⚠️ {warning}")
        else:
            st.success("✅ No behavioral alerts")
        
        # Trading principles reminder
        with st.expander("📚 Trading in the Zone Principles"):
            st.write("✅ Think in probabilities, not predictions")
            st.write("✅ Focus on process over outcomes")
            st.write("✅ Accept uncertainty as natural")
            st.write("✅ Maintain emotional discipline")
            st.write("✅ Stick to your risk management rules")
    
    except Exception as e:
        st.error(f"Error loading behavioral insights: {e}")

def main():
    """Main dashboard function with comprehensive error handling"""
    
    st.title("🎯 Zanalytics Pulse - Advanced Risk Management Dashboard")
    st.markdown("### Scientific Risk Management with Behavioral Psychology Integration")

    # Initialize Pulse Risk Manager
    if 'pulse_manager' not in st.session_state:
        st.session_state.pulse_manager = AdvancedPulseRiskManager()

    pulse_manager = st.session_state.pulse_manager

    # System health status
    health_data = safe_api_call("GET", "pulse/health")
    if "error" not in health_data:
        status = health_data.get("status", "unknown")
        lag = health_data.get("lag_ms", "—")
        st.caption(f"System Status: {status} | Lag: {lag}ms | Last Update: {datetime.now().strftime('%H:%M:%S')}")
    else:
        st.caption(f"System Status: offline | Last Update: {datetime.now().strftime('%H:%M:%S')}")

    # Get account information and risk status
    try:
        account_info = pulse_manager.get_account_info()
        positions_df = pulse_manager.get_positions()
        risk_data = pulse_manager.get_risk_summary()
        confluence_data = pulse_manager.get_confluence_score()
    except Exception as e:
        st.error(f"Error loading data: {e}")
        account_info = {}
        positions_df = pd.DataFrame()
        risk_data = {}
        confluence_data = {}

    # Account banner
    login_banner = account_info.get("login")
    broker_banner = account_info.get("server") or account_info.get("company")
    if login_banner:
        st.markdown(
            f'''
            <div class="market-card" style="text-align:center;">
            <span style="background: #99ffd0; color:#181818; padding:8px 14px; border-radius:12px; font-weight:800;">
            Account {login_banner} • {broker_banner or '—'}
            </span>
            </div>
            ''',
            unsafe_allow_html=True
        )

    # Advanced Risk Control Panel
    render_risk_control_panel(account_info, risk_data)
    
    # Behavioral Psychology Insights
    render_psychology_insights_panel(confluence_data, risk_data)
    
    # Divider
    st.divider()

    # Pulse Decision Surface
    render_pulse_tiles(pulse_manager)
    st.divider()

    # Top metrics row
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric(
            "💰 Balance",
            f"${account_info.get('balance', 0):,.2f}",
            f"${account_info.get('profit', 0):,.2f}"
        )

    with col2:
        equity = account_info.get('equity', 0)
        balance = account_info.get('balance', 1)
        equity_change = ((equity / balance - 1) * 100) if balance > 0 else 0
        
        st.metric(
            "📊 Equity",
            f"${equity:,.2f}",
            f"{equity_change:.2f}%"
        )

    with col3:
        margin_level = account_info.get('margin_level', 0)
        st.metric(
            "🎯 Margin Level",
            f"{margin_level:,.2f}%",
            "Safe" if margin_level > 200 else "Warning"
        )

    with col4:
        risk_used = risk_data.get('daily_risk_used', 0)
        st.metric(
            "📈 Risk Used",
            f"{risk_used:.1f}%",
            f"Phase: {risk_data.get('status', 'Unknown')}"
        )

    with col5:
        st.metric(
            "🔢 Open Positions",
            len(positions_df),
            f"Max: {risk_data.get('max_trades', 5)}"
        )

    # Risk gauges
    st.markdown("---")
    st.subheader("🎯 Risk Metrics")

    gauge_col1, gauge_col2, gauge_col3, gauge_col4 = st.columns(4)

    with gauge_col1:
        fig = create_gauge_chart(risk_data.get('daily_risk_used', 0), "Daily Risk Used (%)")
        st.plotly_chart(fig, use_container_width=True)

    with gauge_col2:
        drawdown = abs(account_info.get('profit', 0)) / account_info.get('balance', 1) * 100 if account_info.get('balance', 0) > 0 else 0
        fig = create_gauge_chart(drawdown, "Current Drawdown (%)")
        st.plotly_chart(fig, use_container_width=True)

    with gauge_col3:
        trades_used = risk_data.get('trades_used', 0)
        max_trades = risk_data.get('max_trades', 5)
        trade_usage = (trades_used / max_trades) * 100 if max_trades > 0 else 0
        fig = create_gauge_chart(trade_usage, "Trade Limit Usage (%)")
        st.plotly_chart(fig, use_container_width=True)

    with gauge_col4:
        overall_risk = min(risk_data.get('daily_risk_used', 0) + drawdown, 100)
        fig = create_gauge_chart(overall_risk, "Overall Risk Score")
        st.plotly_chart(fig, use_container_width=True)

    # Main content area
    col1, col2 = st.columns([2, 1])

    with col1:
        # Trading opportunities
        render_opportunities(pulse_manager)

        # Open positions table
        if not positions_df.empty:
            st.subheader("📋 Open Positions")

            # Format positions dataframe
            display_cols = ['ticket', 'symbol', 'type', 'volume', 'price_open', 
                          'price_current', 'profit', 'time']
            positions_display = positions_df[display_cols].copy()
            positions_display['type'] = positions_display['type'].map({0: 'BUY', 1: 'SELL'})

            # Color code profit/loss
            def color_profit(val):
                color = 'green' if val > 0 else 'red' if val < 0 else 'black'
                return f'color: {color}'

            styled_positions = positions_display.style.applymap(
                color_profit, subset=['profit']
            )

            st.dataframe(styled_positions, use_container_width=True)

    with col2:
        # Behavioral insights
        render_behavioral_insights(pulse_manager)

    # Risk warnings
    st.markdown("---")
    st.subheader("⚠️ Risk Warnings")

    warnings = risk_data.get('warnings', [])
    
    if warnings:
        for warning in warnings:
            st.warning(f"⚠️ {warning}")
    else:
        st.success("✅ All risk parameters within limits")

    # Footer with last update time
    st.markdown("---")
    st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

def create_gauge_chart(value: float, title: str, max_value: float = 100) -> go.Figure:
    """Create a gauge chart for risk metrics"""
    
    # Determine color based on value
    if value < 30:
        color = "green"
    elif value < 70:
        color = "yellow"
    else:
        color = "red"

    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=value,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': title},
        delta={'reference': 50},
        gauge={
            'axis': {'range': [None, max_value]},
            'bar': {'color': color},
            'steps': [
                {'range': [0, 30], 'color': "lightgray"},
                {'range': [30, 70], 'color': "gray"}
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': 90
            }
        }
    ))

    fig.update_layout(height=250, margin=dict(l=20, r=20, t=40, b=20))
    return fig

if __name__ == "__main__":
    main()
