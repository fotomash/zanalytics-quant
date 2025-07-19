import streamlit as st
import toml
# Move set_page_config for "Tick Insights Dashboard" to top
st.set_page_config(
    page_title="Tick Insights Dashboard",
    page_icon="🔎",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- PATCH: Add full-page background image via local asset ---
from PIL import Image
import base64

@st.cache_data
def get_base64_of_bin_file(bin_file_path):
    with open(bin_file_path, "rb") as f:
        data = f.read()
    return base64.b64encode(data).decode()

def set_background(image_file_path):
    bin_str = get_base64_of_bin_file(image_file_path)
    st.markdown(
        f"""
        <style>
        [data-testid="stAppViewContainer"] {{
            background-image: url("data:image/png;base64,{bin_str}");
            background-size: cover;
            background-position: center;
            background-repeat: no-repeat;
            background-attachment: fixed;
        }}
        </style>
        """,
        unsafe_allow_html=True
    )
# Set fixed full-page background image using local asset
try:
    set_background("./theme/image_af247b.jpg")
except Exception:
    st.warning("Background image file not found or could not be loaded.")

# Ensure background and CSS are set before any data imports
st.markdown("""
<style>
.main .block-container {
    max-width: 998px !important;
    padding-left: 1.5vw;
    padding-right: 1.5vw;
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<style>
section[data-testid="stSidebar"] {
    background-color: rgba(0,0,0,0.8) !important;
    box-shadow: none !important;
}
</style>
""", unsafe_allow_html=True)
st.markdown("""
<style>
[data-testid="stAppViewContainer"] {
    background-color: #000 !important;
    background-image: none !important;
}
</style>
""", unsafe_allow_html=True)
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
# ... other imports

# --- Ensure project root and /core directory are on PYTHONPATH ---
import sys, os
_ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_CORE_DIR = os.path.join(_ROOT_DIR, "core")
for _p in (_ROOT_DIR, _CORE_DIR):
    if _p not in sys.path:
        sys.path.append(_p)

# ---- Tick Vectorizer Integration ----
from utils.tick_vectorizer import TickVectorizer, VectorizedDashboard

# --- Robust optional imports: gracefully degrade if modules are missing ---
try:
    from core.micro_wyckoff_phase_engine import detect_micro_wyckoff_phase as detect_wyckoff_phases
except (ImportError, ModuleNotFoundError):
    def detect_wyckoff_phases(df):
        """Stub fallback when `micro_wyckoff_phase_engine` is unavailable."""
        return []

try:
    from core.impulse_correction_detector import detect_impulse_patterns
except (ImportError, ModuleNotFoundError):
    def detect_impulse_patterns(df):
        """Stub fallback when `impulse_correction_detector` is unavailable."""
        return []

# ---- Core microstructure modules ----

# TODO: remove or replace when microstructure_filter is available – # apply_microstructure_filter(
# from core.scalp_filters import detect_scalp_conditions
# --- Optional import for SMC enrichment logic ---
try:
    from core.smc_enrichment_engine import enrich_with_smc_logic
except (ImportError, ModuleNotFoundError, AttributeError):
    def enrich_with_smc_logic(df):
        """
        Fallback stub: safely returns the input dataframe unchanged when the
        real `enrich_with_smc_logic` implementation is unavailable.
        """
        return df


class QRTDeskAnalytics:
    def __init__(self):
        self.session_state = {}

    def detect_liquidity_sweeps(self, df: pd.DataFrame) -> Dict:
        """
        Detect rapid price moves that sweep through multiple price levels in a short burst (liquidity sweeps).
        Returns a dictionary with detected sweep events and summary metrics.
        """
        sweep_events = []
        threshold_move = df['price_mid'].std() * 3  # 3 std dev move
        window = 5  # ticks
        for i in range(window, len(df)):
            price_window = df['price_mid'].iloc[i-window:i]
            move = price_window.iloc[-1] - price_window.iloc[0]
            if abs(move) > threshold_move:
                sweep_events.append({
                    'start_time': df['timestamp'].iloc[i-window],
                    'end_time': df['timestamp'].iloc[i-1],
                    'direction': 'up' if move > 0 else 'down',
                    'magnitude': move,
                    'volume': df['inferred_volume'].iloc[i-window:i].sum()
                })
        return {'sweep_events': sweep_events, 'count': len(sweep_events)}

    def detect_liquidity_sweeps_enhanced(self, df: pd.DataFrame) -> Dict:
        """Enhanced liquidity sweep detection with multiple patterns"""
        # --- Helper & pre‑compute additions (upgrade v2) ---
        def _sigmoid(x: float) -> float:
            """Numerically‑stable sigmoid for risk scoring."""
            return 1 / (1 + np.exp(-x))

        # Ensure pressure columns exist for imbalance calc
        if 'bid_pressure' not in df.columns:
            df['bid_pressure'] = df['bid'].diff()
        if 'ask_pressure' not in df.columns:
            df['ask_pressure'] = df['ask'].diff()

        # Pre‑compute a simple price‑level liquidity heat‑map
        vol_by_level = df.groupby(df['price_mid'].round(0))['inferred_volume'].sum().to_dict()

        sweep_events = []

        # Calculate rolling metrics
        df['price_velocity'] = df['price_mid'].diff() / (df['tick_interval_ms'] + 1)
        df['volume_surge'] = df['inferred_volume'] / df['inferred_volume'].rolling(20).mean()
        df['directional_pressure'] = df['price_mid'].diff().rolling(5).apply(
            lambda x: (x > 0).sum() / len(x) if len(x) > 0 else 0.5
        )

        # Pattern 1: Stop‑hunt sweeps
        price_std = df['price_mid'].rolling(50).std()
        df['price_deviation'] = (df['price_mid'] - df['price_mid'].rolling(50).mean()) / price_std

        # Pattern 2: Volume‑driven sweeps
        for i in range(10, len(df) - 5):
            window = df.iloc[i-5:i+5]

            # Rapid price movement
            price_move = abs(window['price_mid'].iloc[-1] - window['price_mid'].iloc[0])
            price_move_bps = (price_move / window['price_mid'].iloc[0]) * 10000

            if price_move_bps > 10:                                       # ≥10 bps
                t_ms = (window['timestamp'].iloc[-1] - window['timestamp'].iloc[0]).total_seconds() * 1000
                if t_ms < 500:                                            # within 500 ms
                    avg_vol = window['inferred_volume'].mean()
                    baseline_vol = df['inferred_volume'].iloc[:i-5].tail(50).mean()

                    if avg_vol > baseline_vol * 2.5:                      # volume surge
                        direction = 'up' if window['price_mid'].iloc[-1] > window['price_mid'].iloc[0] else 'down'

                        # reversal test for stop‑hunt
                        if i + 10 < len(df):
                            fut = df.iloc[i:i+10]
                            rev_price = fut['price_mid'].iloc[-1]
                            is_stop = (
                                (direction == 'up' and rev_price < window['price_mid'].iloc[-1] - price_move * 0.5) or
                                (direction == 'down' and rev_price > window['price_mid'].iloc[-1] + price_move * 0.5)
                            )
                        else:
                            is_stop = False

                        # --- Enriched feature set & risk scoring ---
                        speed_ms = window['tick_interval_ms'].sum()
                        vwap = (
                            (window['price_mid'] * window['inferred_volume']).sum()
                            / max(window['inferred_volume'].sum(), 1e-9)
                        )
                        vwap_delta_bps = ((window['price_mid'].iloc[-1] - vwap) / vwap) * 1e4

                        pressure_imb = (
                            df['bid_pressure'].iloc[i] - df['ask_pressure'].iloc[i]
                            if ('bid_pressure' in df.columns and 'ask_pressure' in df.columns)
                            else 0.0
                        )

                        # Liquidity heat (approx.) at sweep start/end rounded to 1‑pip
                        lvl_start = round(window['price_mid'].iloc[0], 0)
                        lvl_end   = round(window['price_mid'].iloc[-1], 0)
                        heat_pre  = vol_by_level.get(lvl_start, 0.0)
                        heat_post = vol_by_level.get(lvl_end,   0.0)

                        # Feature vector for ML downstream
                        event_features = np.array([
                            price_move_bps,
                            avg_vol / baseline_vol,
                            speed_ms,
                            vwap_delta_bps,
                            pressure_imb,
                            heat_post - heat_pre
                        ])

                        # Composite raw risk score
                        risk_raw = (
                            (price_move_bps / 10)
                            + (avg_vol / baseline_vol)
                            + (abs(pressure_imb) / 1e5)
                            - (speed_ms / 500)
                            + (abs(vwap_delta_bps) / 10)
                        )
                        risk_score = float(_sigmoid(risk_raw))

                        sweep_events.append({
                            'type': 'stop_hunt' if is_stop else 'liquidity_grab',
                            'start_time': window['timestamp'].iloc[0],
                            'end_time': window['timestamp'].iloc[-1],
                            'direction': direction,
                            'magnitude_bps': price_move_bps,
                            'volume_surge': avg_vol / baseline_vol,
                            'ms_per_sweep': speed_ms,
                            'vwap_delta_bps': vwap_delta_bps,
                            'pressure_imbalance': pressure_imb,
                            'heat_pre': heat_pre,
                            'heat_post': heat_post,
                            'risk_score': risk_score,
                            'features': event_features.tolist(),
                            'tick_count': len(window),
                            'reversal_detected': is_stop,
                            'regime': self.session_state.get('market_regime', 'unknown'),
                            'confidence': risk_score
                        })

        return {
            'sweep_events': sweep_events,
            'count': len(sweep_events),
            'stop_hunts': sum(1 for e in sweep_events if e['type'] == 'stop_hunt'),
            'liquidity_grabs': sum(1 for e in sweep_events if e['type'] == 'liquidity_grab'),
            'avg_risk_score': np.mean([e['risk_score'] for e in sweep_events]) if sweep_events else 0.0
        }

    def calculate_tick_microstructure_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate microstructure features at the tick level for predictive analytics.
        Returns the dataframe with new feature columns appended.
        """
        df['micro_return'] = df['price_mid'].pct_change().fillna(0)
        df['volatility_5'] = df['price_mid'].rolling(5).std().fillna(0)
        df['volatility_20'] = df['price_mid'].rolling(20).std().fillna(0)
        df['spread_z'] = (df['spread'] - df['spread'].mean()) / (df['spread'].std() + 1e-9)
        df['tick_imbalance'] = (df['bid'] - df['ask']) / (df['bid'] + df['ask'] + 1e-9)
        return df

    def compute_execution_quality_metrics(self, df: pd.DataFrame) -> Dict:
        """Calculate execution quality metrics from tick data only"""
        metrics = {}

        # 1. Tick-based liquidity metrics (no trades needed)
        metrics['avg_quoted_spread'] = df['spread'].mean()
        metrics['median_spread'] = df['spread'].median()
        metrics['spread_volatility'] = df['spread'].std()

        # 2. Effective spread proxy (tick-to-tick price changes)
        df['price_mid'] = (df['bid'] + df['ask']) / 2
        df['tick_move'] = df['price_mid'].diff().abs()
        metrics['avg_tick_move'] = df['tick_move'].mean()
        metrics['effective_spread_proxy'] = 2 * metrics['avg_tick_move']

        # 3. Liquidity provision cost
        df['spread_bps'] = (df['spread'] / df['price_mid']) * 10000
        metrics['avg_spread_bps'] = df['spread_bps'].mean()

        # 4. Price impact proxy (using inferred volume)
        if 'inferred_volume' in df.columns:
            df['price_impact'] = df['tick_move'] / (df['inferred_volume'] + 1)
            metrics['kyle_lambda'] = df['price_impact'].rolling(100).mean().iloc[-1]
        else:
            metrics['kyle_lambda'] = np.nan

        # 5. Adverse selection indicator
        df['spread_tightness'] = 1 / (df['spread'] + 0.0001)
        df['future_volatility'] = df['price_mid'].pct_change().rolling(20).std().shift(-20)
        tight_spread_mask = df['spread'] < df['spread'].quantile(0.25)
        if tight_spread_mask.any() and df['future_volatility'].notna().any():
            metrics['adverse_selection_score'] = (
                df[tight_spread_mask]['future_volatility'].mean() /
                df['future_volatility'].mean()
            )
        else:
            metrics['adverse_selection_score'] = 1.0

        # 6. Execution favorability windows
        df['spread_volatility'] = df['spread'].rolling(20).std().fillna(method='bfill')
        df['execution_score'] = (
            (1 - df['spread'] / df['spread'].rolling(1000).max()) * 0.5 +
            (1 - df['spread_volatility'].rolling(100).mean() / df['spread_volatility'].max()) * 0.5
        )
        metrics['current_exec_favorability'] = df['execution_score'].iloc[-1] if 'execution_score' in df.columns else 0.5

        return metrics

    def identify_killzone_patterns(self, df: pd.DataFrame) -> Dict:
        """
        Identify killzone patterns (e.g., London/NY open sweeps) in the tick data.
        Returns a dictionary with detected killzone events and summary stats.
        """
        killzone_events = []
        # Assume timestamp in UTC, killzones: London 07:00-10:00, NY 12:00-15:00 UTC
        df['hour'] = df['timestamp'].dt.hour
        for start, end, label in [(7, 10, 'London'), (12, 15, 'NY')]:
            mask = (df['hour'] >= start) & (df['hour'] < end)
            zone_df = df[mask]
            if not zone_df.empty:
                move = zone_df['price_mid'].iloc[-1] - zone_df['price_mid'].iloc[0]
                killzone_events.append({
                    'zone': label,
                    'start_time': zone_df['timestamp'].iloc[0],
                    'end_time': zone_df['timestamp'].iloc[-1],
                    'move': move,
                    'volume': zone_df['inferred_volume'].sum()
                })
        return {'killzone_events': killzone_events, 'count': len(killzone_events)}
import streamlit as st

# --- Intelligence Report (LLM, pro UX) --------------------------------------
import time

def generate_intelligence_report(df: pd.DataFrame, client) -> str:
    """
    Get chart-by-chart insights using the zanalytics_midas model.
    """
    prompt = f"""
    You are a financial microstructure analyst specializing in engineered liquidity
    and order-flow interpretation.

    Analyse the following tick snapshot and write concise, data-driven commentary
    for each of these dashboard sections:
    • 📈 Price vs Inferred Volume  
    • ↔️ Spread Behaviour  
    • 🔥 VPIN (Flow Toxicity)  
    • 📊 Wyckoff Phase Inference  
    • 🧠 Regime Transition Signals  
    • 📍 Scalp Entry Conditions  

    Tick Snapshot (first 25 rows):
    {df.head(25).to_json(orient="records", date_format="iso")}
    """
    response = client.chat.completions.create(
        model="zanalytics_midas",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.4
    )
    return response.choices[0].message.content.strip()

# --- Button-triggered Intelligence Report (with cache/progress/last updated) ---
import datetime

report_placeholder = st.empty()
status_placeholder = st.empty()

if 'intelligence_report' not in st.session_state:
    st.session_state['intelligence_report'] = None
    st.session_state['intelligence_report_time'] = None

if st.button("🧠 Generate Tick Intelligence Report", key="generate_tick_report"):
    with st.spinner("Generating intelligence report..."):
        try:
            commentary = generate_intelligence_report(df, client)
            st.session_state['intelligence_report'] = commentary
            st.session_state['intelligence_report_time'] = datetime.datetime.now()
        except Exception as e:
            st.session_state['intelligence_report'] = "Intelligence report currently unavailable."
            st.session_state['intelligence_report_time'] = datetime.datetime.now()

# Always display last report and updated time (if any)
if st.session_state['intelligence_report']:
    report_placeholder.markdown(st.session_state['intelligence_report'])
    if st.session_state['intelligence_report_time']:
        status_placeholder.caption(f"Last updated: {st.session_state['intelligence_report_time'].strftime('%Y-%m-%d %H:%M:%S')}")
else:
    report_placeholder.info("No intelligence report generated yet. Click the button above to run your tick intelligence analysis.")
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px
from datetime import datetime, timedelta
from scipy import stats, signal
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import DBSCAN
import yaml
import os
from typing import Dict, List, Tuple, Optional
import warnings
warnings.filterwarnings('ignore')

class QuantumMicrostructureAnalyzer:
    # ------------------- New Methods: UX & Automation Features -------------------
    def setup_realtime_alerts(self):
        """Initialize or reset real-time alert system for regime changes, trap predictions, etc."""
        self.session_state.setdefault('regime_alerts', [])
        self.session_state.setdefault('last_regime', None)
        self.session_state.setdefault('trap_alerts', [])
        self.session_state.setdefault('pattern_search_results', [])

    def check_regime_alerts(self, current_regime, df):
        """Display real-time regime alerts if regime has changed."""
        if self.session_state.get('last_regime') != current_regime:
            st.warning(f"⚡ Market regime changed: {current_regime.upper()}")
            self.session_state['regime_alerts'].append({
                'timestamp': df['timestamp'].iloc[-1] if not df.empty else None,
                'regime': current_regime
            })
            self.session_state['last_regime'] = current_regime

    def create_pattern_snapshot(self, df, session_state):
        """Create a JSON-serializable snapshot of key patterns and session state."""
        import json
        snapshot = {
            'timestamp': str(df['timestamp'].iloc[-1]) if not df.empty else None,
            'iceberg_events': session_state.get('iceberg_events', []),
            'spoofing_events': session_state.get('spoofing_events', []),
            'trap_events': session_state.get('trap_events', []),
            'market_regime': session_state.get('market_regime', 'unknown'),
            'manipulation_score': session_state.get('manipulation_score', 0),
        }
        return json.dumps(snapshot, default=str, indent=2)

    def render_download_buttons(self, snapshot):
        """Render download buttons for exporting pattern snapshot as JSON."""
        st.download_button(
            label="📥 Download Pattern Snapshot (JSON)",
            data=snapshot,
            file_name="pattern_snapshot.json",
            mime="application/json"
        )

    def create_pattern_search_interface(self):
        """Render a Streamlit UI for searching patterns in session events."""
        st.markdown("#### 🔍 Pattern Search")
        pattern = st.text_input("Enter pattern or keyword (e.g. 'iceberg', 'trap', 'spoofing')", "")
        if pattern:
            results = []
            for key in ['iceberg_events', 'spoofing_events', 'trap_events']:
                events = self.session_state.get(key, [])
                for e in events:
                    if pattern.lower() in str(e).lower():
                        results.append({'type': key, **e})
            self.session_state['pattern_search_results'] = results
            if results:
                st.write(f"Found {len(results)} matching events:")
                st.dataframe(pd.DataFrame(results))
            else:
                st.info("No matching events found.")

    def execute_pattern_search(self, pattern):
        """Search session events for a pattern/keyword."""
        results = []
        for key in ['iceberg_events', 'spoofing_events', 'trap_events']:
            events = self.session_state.get(key, [])
            for e in events:
                if pattern.lower() in str(e).lower():
                    results.append({'type': key, **e})
        return results

    def create_trap_predictor(self):
        """Initialize a simple ML or heuristic-based trap predictor (stub example)."""
        # This could be replaced by loading a real model
        self.trap_predictor = lambda df: {
            'trap_probability': np.clip(np.random.normal(0.15, 0.08), 0, 1),
            'suggested_action': "AVOID LONG" if np.random.rand() > 0.5 else "AVOID SHORT"
        }

    def predict_next_trap(self, df):
        """Predict the probability of a trap event in the next N ticks."""
        if hasattr(self, 'trap_predictor'):
            return self.trap_predictor(df)
        else:
            return {'trap_probability': 0.0, 'suggested_action': "NONE"}

    def create_event_correlation_matrix(self, df):
        """Display a correlation matrix of event types and microstructure features."""
        st.markdown("#### 📈 Event Correlation Matrix")
        # Example: correlate spoofing/iceberg/trap events with features
        feature_cols = ['spread', 'tick_rate', 'vpin', 'inferred_volume']
        event_cols = []
        for key in ['iceberg_events', 'spoofing_events', 'trap_events']:
            if self.session_state.get(key):
                event_df = pd.DataFrame(self.session_state[key])
                if not event_df.empty and 'timestamp' in event_df:
                    df_key = df.set_index('timestamp')
                    event_mask = df['timestamp'].isin(event_df['timestamp'])
                    df.loc[event_mask, f"{key}_flag"] = 1
                    df.loc[~event_mask, f"{key}_flag"] = 0
                    event_cols.append(f"{key}_flag")
        if event_cols:
            corr = df[feature_cols + event_cols].corr()
            st.dataframe(corr.round(2))
        else:
            st.info("No event flags available for correlation matrix.")

    def generate_session_narrative(self, df, session_state):
        """Generate a human-readable narrative summary for the analyzed session."""
        from datetime import datetime
        start = str(df['timestamp'].iloc[0]) if not df.empty else ''
        end = str(df['timestamp'].iloc[-1]) if not df.empty else ''
        iceberg_count = len(session_state.get('iceberg_events', []))
        spoof_count = len(session_state.get('spoofing_events', []))
        regime = session_state.get('market_regime', 'unknown')
        manip_score = session_state.get('manipulation_score', 0)
        narrative = (
            f"**Session Analysis** ({start} → {end})\n\n"
            f"- Market regime: **{regime.upper()}**\n"
            f"- Manipulation score: **{manip_score:.2f}**\n"
            f"- Iceberg orders detected: **{iceberg_count}**\n"
            f"- Spoofing events detected: **{spoof_count}**\n"
            f"- VPIN average: **{df['vpin'].mean():.3f}**\n"
        )
        if manip_score > 5:
            narrative += "\n⚠️  High manipulation score: caution is advised for active trading."
        return narrative

    def generate_pdf_report(self, df, snapshot, narrative):
        """Generate a simple PDF report of the analysis."""
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
        import tempfile
        pdf_path = tempfile.mktemp(suffix=".pdf")
        c = canvas.Canvas(pdf_path, pagesize=letter)
        width, height = letter
        c.setFont("Helvetica", 12)
        c.drawString(30, height-40, "Quantum Microstructure Analysis Report")
        c.setFont("Helvetica", 10)
        c.drawString(30, height-60, f"Session: {str(df['timestamp'].iloc[0])} → {str(df['timestamp'].iloc[-1])}")
        c.drawString(30, height-80, f"Market Regime: {self.session_state.get('market_regime', 'unknown')}")
        c.drawString(30, height-100, f"Manipulation Score: {self.session_state.get('manipulation_score', 0):.2f}")
        c.drawString(30, height-120, f"Iceberg Orders: {len(self.session_state.get('iceberg_events', []))}")
        c.drawString(30, height-140, f"Spoofing Events: {len(self.session_state.get('spoofing_events', []))}")
        c.setFont("Helvetica", 9)
        c.drawString(30, height-170, "Session Narrative:")
        text_obj = c.beginText(30, height-190)
        for line in narrative.split('\n'):
            text_obj.textLine(line)
        c.drawText(text_obj)
        c.setFont("Helvetica", 8)
        c.drawString(30, height-350, "Pattern Snapshot:")
        snap_lines = snapshot.split('\n')
        snap_text = c.beginText(30, height-370)
        for line in snap_lines[:20]:
            snap_text.textLine(line)
        c.drawText(snap_text)
        c.save()
        return pdf_path
    def create_liquidity_sweep_visualization(self, df: pd.DataFrame, sweep_events: List[Dict]) -> None:
        """Comprehensive liquidity‑sweep visualisation"""
        if not sweep_events:
            return

        sweep_df = pd.DataFrame(sweep_events)

        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=(
                'Price Action with Sweeps',
                'Sweep Magnitude Distribution',
                'Volume Surge Analysis',
                'Sweep Type Breakdown'
            ),
            specs=[[{"secondary_y": True}, {}],
                   [{}, {"type": "pie"}]]
        )

        # 1 – price trace with sweep markers
        fig.add_trace(
            go.Scatter(x=df['timestamp'], y=df['price_mid'],
                       name='Price', line=dict(color='gray', width=1)),
            row=1, col=1
        )
        for _, sw in sweep_df.iterrows():
            colour = 'red' if sw['type'] == 'stop_hunt' else 'orange'
            fig.add_trace(
                go.Scatter(
                    x=[sw['start_time'], sw['end_time']],
                    y=[df.loc[df['timestamp'] == sw['start_time'], 'price_mid'].iloc[0],
                       df.loc[df['timestamp'] == sw['end_time'],   'price_mid'].iloc[0]],
                    mode='lines+markers',
                    line=dict(color=colour, width=3),
                    marker=dict(size=10),
                    name=sw['type'],
                    showlegend=False
                ),
                row=1, col=1
            )

        # 2 – magnitude histogram
        fig.add_trace(
            go.Histogram(x=sweep_df['magnitude_bps'], nbinsx=20, name='Magnitude (bps)'),
            row=1, col=2
        )

        # 3 – volume‑surge scatter
        fig.add_trace(
            go.Scatter(
                x=sweep_df['magnitude_bps'],
                y=sweep_df['volume_surge'],
                mode='markers',
                marker=dict(size=sweep_df['confidence']*20,
                            color=sweep_df['tick_count'],
                            colorscale='Viridis', showscale=True),
                text=[f"{t} ticks" for t in sweep_df['tick_count']],
                name='Volume surge'
            ),
            row=2, col=1
        )

        # 4 – sweep‑type pie
        type_counts = sweep_df['type'].value_counts()
        fig.add_trace(
            go.Pie(labels=type_counts.index, values=type_counts.values),
            row=2, col=2
        )

        fig.update_layout(height=800, showlegend=True)
        st.plotly_chart(fig, use_container_width=True)

    # ---- Enhanced Micro-Wyckoff, Session Liquidity & Trap Detection ----

    def detect_micro_wyckoff_events(self, df: pd.DataFrame) -> Dict:
        """Detect tick-level Wyckoff patterns as per TickLevel_MicroWyckoff_EventScorer_v12"""
        events = {
            'micro_springs': [],
            'micro_utads': [],
            'micro_tests': [],
            'tick_chochs': []
        }
        df['micro_swing_high'] = df['price_mid'].rolling(10).max()
        df['micro_swing_low'] = df['price_mid'].rolling(10).min()
        df['volume_ma'] = df['inferred_volume'].rolling(20).mean()
        for i in range(20, len(df) - 5):
            window = df.iloc[i-10:i+5]
            # Micro-Spring detection
            if (window['price_mid'].iloc[5] < window['micro_swing_low'].iloc[5] and
                window['price_mid'].iloc[-1] > window['price_mid'].iloc[5] and
                window['inferred_volume'].iloc[5] > window['volume_ma'].iloc[5] * 2):
                events['micro_springs'].append({
                    'timestamp': window['timestamp'].iloc[5],
                    'sweep_price': window['price_mid'].iloc[5],
                    'rejection_price': window['price_mid'].iloc[-1],
                    'volume_spike': window['inferred_volume'].iloc[5] / window['volume_ma'].iloc[5],
                    'tick_velocity': (window['price_mid'].iloc[-1] - window['price_mid'].iloc[5]) /
                                     (window['tick_interval_ms'].iloc[5:].sum() + 1),
                    'confidence': min(window['inferred_volume'].iloc[5] / window['volume_ma'].iloc[5] / 3, 1.0)
                })
            # Micro-UTAD detection
            if (window['price_mid'].iloc[5] > window['micro_swing_high'].iloc[5] and
                window['price_mid'].iloc[-1] < window['price_mid'].iloc[5] and
                window['inferred_volume'].iloc[5] > window['volume_ma'].iloc[5] * 2):
                events['micro_utads'].append({
                    'timestamp': window['timestamp'].iloc[5],
                    'sweep_price': window['price_mid'].iloc[5],
                    'rejection_price': window['price_mid'].iloc[-1],
                    'volume_spike': window['inferred_volume'].iloc[5] / window['volume_ma'].iloc[5],
                    'confidence': min(window['inferred_volume'].iloc[5] / window['volume_ma'].iloc[5] / 3, 1.0)
                })
        return events

    def analyze_session_liquidity_patterns(self, df: pd.DataFrame) -> Dict:
        """Detect session-specific patterns like Judas Swing"""
        patterns = {
            'asia_range': None,
            'london_judas': [],
            'ny_continuations': []
        }
        df['hour'] = df['timestamp'].dt.hour
        df['session'] = 'other'
        df.loc[(df['hour'] >= 0) & (df['hour'] < 7), 'session'] = 'asia'
        df.loc[(df['hour'] >= 7) & (df['hour'] < 12), 'session'] = 'london'
        df.loc[(df['hour'] >= 12) & (df['hour'] < 20), 'session'] = 'ny'
        asia_data = df[df['session'] == 'asia']
        if not asia_data.empty:
            patterns['asia_range'] = {
                'high': asia_data['price_mid'].max(),
                'low': asia_data['price_mid'].min(),
                'avg_volume': asia_data['inferred_volume'].mean()
            }
        london_data = df[df['session'] == 'london']
        if not london_data.empty and patterns['asia_range']:
            london_open = london_data.iloc[:min(300, len(london_data))]
            if london_open['price_mid'].max() > patterns['asia_range']['high']:
                sweep_idx = london_open['price_mid'].idxmax()
                if sweep_idx + 50 < len(df):
                    post_sweep = df.iloc[sweep_idx:sweep_idx+50]
                    if post_sweep['price_mid'].iloc[-1] < patterns['asia_range']['high']:
                        patterns['london_judas'].append({
                            'type': 'bearish_judas',
                            'sweep_time': df.loc[sweep_idx, 'timestamp'],
                            'sweep_price': df.loc[sweep_idx, 'price_mid'],
                            'asia_level': patterns['asia_range']['high'],
                            'rejection_depth': (df.loc[sweep_idx, 'price_mid'] - post_sweep['price_mid'].min()),
                            'volume_ratio': london_open['inferred_volume'].mean() / patterns['asia_range']['avg_volume']
                        })
        return patterns

    def detect_inducement_traps(self, df: pd.DataFrame) -> list:
        """Detect engineered liquidity traps with tick precision"""
        traps = []
        df['swing_high'] = df['price_mid'].rolling(20).max()
        df['swing_low'] = df['price_mid'].rolling(20).min()
        price_levels = df['price_mid'].round(4).value_counts()
        significant_levels = price_levels[price_levels >= 3].index
        for level in significant_levels:
            level_touches = df[abs(df['price_mid'] - level) < 0.0001]
            if len(level_touches) >= 3:
                sweep_candidates = df[
                    ((df['price_mid'] > level + 0.0001) & (df.index > level_touches.index[-1])) |
                    ((df['price_mid'] < level - 0.0001) & (df.index > level_touches.index[-1]))
                ]
                if not sweep_candidates.empty:
                    sweep_idx = sweep_candidates.index[0]
                    if sweep_idx + 20 < len(df):
                        post_sweep = df.iloc[sweep_idx:sweep_idx+20]
                        if ((df.loc[sweep_idx, 'price_mid'] > level and post_sweep['price_mid'].min() < level) or
                            (df.loc[sweep_idx, 'price_mid'] < level and post_sweep['price_mid'].max() > level)):
                            snapback_velocity = abs(
                                post_sweep['price_mid'].iloc[-1] - df.loc[sweep_idx, 'price_mid']
                            ) / (post_sweep['tick_interval_ms'].sum() + 1)
                            traps.append({
                                'type': 'inducement_sweep',
                                'level': level,
                                'sweep_time': df.loc[sweep_idx, 'timestamp'],
                                'sweep_price': df.loc[sweep_idx, 'price_mid'],
                                'snapback_velocity': snapback_velocity,
                                'volume_surge': df.loc[sweep_idx, 'inferred_volume'] /
                                                df['inferred_volume'].rolling(20).mean().loc[sweep_idx],
                                'touches_before_sweep': len(level_touches),
                                'confidence': min(snapback_velocity * 1000 *
                                                  (df.loc[sweep_idx, 'inferred_volume'] / df['inferred_volume'].mean()), 1.0)
                            })
        return traps

    def create_enhanced_manipulation_section(self, df: pd.DataFrame):
        """Enhanced manipulation detection with strategy-specific patterns"""
        import plotly.graph_objects as go
        st.markdown("### 🎯 Advanced Pattern Recognition")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### Micro-Wyckoff Events")
            wyckoff_events = self.detect_micro_wyckoff_events(df)
            total_events = sum(len(events) for events in wyckoff_events.values())
            if total_events > 0:
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Micro-Springs", len(wyckoff_events['micro_springs']))
                m2.metric("Micro-UTADs", len(wyckoff_events['micro_utads']))
                m3.metric("Micro-Tests", len(wyckoff_events['micro_tests']))
                m4.metric("Tick-CHoCHs", len(wyckoff_events['tick_chochs']))
                fig_wyck = go.Figure()
                fig_wyck.add_trace(go.Scatter(
                    x=df['timestamp'], y=df['price_mid'],
                    mode='lines', name='Price',
                    line=dict(color='lightgray', width=1)
                ))
                if wyckoff_events['micro_springs']:
                    springs_df = pd.DataFrame(wyckoff_events['micro_springs'])
                    fig_wyck.add_trace(go.Scatter(
                        x=springs_df['timestamp'],
                        y=springs_df['sweep_price'],
                        mode='markers',
                        name='Micro-Springs',
                        marker=dict(
                            symbol='triangle-up',
                            size=10,
                            color='green',
                            opacity=springs_df['confidence']
                        )
                    ))
                if wyckoff_events['micro_utads']:
                    utads_df = pd.DataFrame(wyckoff_events['micro_utads'])
                    fig_wyck.add_trace(go.Scatter(
                        x=utads_df['timestamp'],
                        y=utads_df['sweep_price'],
                        mode='markers',
                        name='Micro-UTADs',
                        marker=dict(
                            symbol='triangle-down',
                            size=10,
                            color='red',
                            opacity=utads_df['confidence']
                        )
                    ))
                fig_wyck.update_layout(
                    title="Micro-Wyckoff Pattern Detection",
                    xaxis_title="Time",
                    yaxis_title="Price",
                    height=400
                )
                st.plotly_chart(fig_wyck, use_container_width=True)
            else:
                st.info("No micro-Wyckoff events detected")
        with col2:
            st.markdown("#### Session Liquidity Patterns")
            session_patterns = self.analyze_session_liquidity_patterns(df)
            if session_patterns['london_judas']:
                judas_df = pd.DataFrame(session_patterns['london_judas'])
                fig_judas = go.Figure()
                for session in ['asia', 'london', 'ny']:
                    session_data = df[df['session'] == session]
                    if not session_data.empty:
                        fig_judas.add_vrect(
                            x0=session_data['timestamp'].iloc[0],
                            x1=session_data['timestamp'].iloc[-1],
                            fillcolor={'asia': 'lightblue', 'london': 'lightgreen', 'ny': 'lightyellow'}[session],
                            opacity=0.2,
                            layer="below",
                            line_width=0,
                        )
                fig_judas.add_trace(go.Scatter(
                    x=df['timestamp'], y=df['price_mid'],
                    mode='lines', name='Price',
                    line=dict(color='black', width=1)
                ))
                if session_patterns['asia_range']:
                    asia_data = df[df['session'] == 'asia']
                    if not asia_data.empty:
                        fig_judas.add_hline(
                            y=session_patterns['asia_range']['high'],
                            line_dash="dash", line_color="blue",
                            annotation_text="Asia High"
                        )
                        fig_judas.add_hline(
                            y=session_patterns['asia_range']['low'],
                            line_dash="dash", line_color="blue",
                            annotation_text="Asia Low"
                        )
                for judas in session_patterns['london_judas']:
                    fig_judas.add_trace(go.Scatter(
                        x=[judas['sweep_time']],
                        y=[judas['sweep_price']],
                        mode='markers+text',
                        name='Judas Sweep',
                        marker=dict(
                            symbol='x',
                            size=15,
                            color='red' if judas['type'] == 'bearish_judas' else 'green'
                        ),
                        text=[judas['type']],
                        textposition="top center"
                    ))
                fig_judas.update_layout(
                    title="Session-Based Liquidity Analysis",
                    xaxis_title="Time",
                    yaxis_title="Price",
                    height=400
                )
                st.plotly_chart(fig_judas, use_container_width=True)
                st.markdown("##### Judas Swing Statistics")
                st.dataframe(judas_df[['type', 'sweep_time', 'asia_level',
                                       'rejection_depth', 'volume_ratio']].round(4))
            else:
                st.info("No Judas patterns detected in current session")
        st.markdown("#### 🪤 Inducement & Engineered Liquidity Traps")
        trap_events = self.detect_inducement_traps(df)
        if trap_events:
            trap_df = pd.DataFrame(trap_events)
            fig_traps = go.Figure()
            fig_traps.add_trace(go.Scatter(
                x=df['timestamp'], y=df['price_mid'],
                mode='lines', name='Price',
                line=dict(color='gray', width=1)
            ))
            for _, trap in trap_df.iterrows():
                fig_traps.add_trace(go.Scatter(
                    x=[trap['sweep_time']],
                    y=[trap['sweep_price']],
                    mode='markers+text',
                    name='Trap',
                    marker=dict(
                        symbol='star',
                        size=15,
                        color='purple',
                        opacity=trap['confidence']
                    ),
                    text=[f"Trap @ {trap['level']:.4f}"],
                    textposition="top center",
                    showlegend=False
                ))
                fig_traps.add_hline(
                    y=trap['level'],
                    line_dash="dot",
                    line_color="purple",
                    opacity=0.5
                )
            fig_traps.update_layout(
                title="Inducement & Liquidity Trap Detection",
                xaxis_title="Time",
                yaxis_title="Price",
                height=400
            )
            st.plotly_chart(fig_traps, use_container_width=True)
            col1, col2, col3 = st.columns(3)
            col1.metric("Total Traps", len(trap_df))
            col2.metric("Avg Snapback Velocity", f"{trap_df['snapback_velocity'].mean():.6f}")
            col3.metric("Avg Volume Surge", f"{trap_df['volume_surge'].mean():.2f}x")
            st.dataframe(
                trap_df[['sweep_time', 'level', 'snapback_velocity',
                         'volume_surge', 'touches_before_sweep', 'confidence']].round(4),
                use_container_width=True
            )
        else:
            st.info("No inducement traps detected")

    def generate_manipulation_vectors(self, df: pd.DataFrame, events: Dict) -> np.ndarray:
        """Generate 1536-dim vectors for manipulation events"""
        vectors = []
        for event_type, event_list in events.items():
            for event in event_list:
                features = []
                if 'confidence' in event:
                    features.append(event['confidence'])
                if 'volume_surge' in event:
                    features.append(min(event['volume_surge'] / 5, 1.0))
                if 'snapback_velocity' in event:
                    features.append(min(event['snapback_velocity'] * 1000, 1.0))
                feature_vector = np.zeros(1536)
                feature_vector[:len(features)] = features
                feature_vector[len(features):] = np.random.randn(1536 - len(features)) * 0.01
                vectors.append(feature_vector)
        return np.array(vectors) if vectors else np.empty((0, 1536))
    def __init__(self, config_path: str):
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)['quantum_analysis_config']

        self.session_state = {
            'inferred_volumes': [],
            'iceberg_events': [],
            'spoofing_events': [],
            'manipulation_score': 0,
            'manipulation_score': 0,
            'market_regime': 'normal',
            'toxic_flow_periods': [],
            'hidden_liquidity_map': {}
        }
        self.setup_realtime_alerts()
        # If you want ML trap prediction:
        self.create_trap_predictor()

    def preprocess_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Ensure all required columns exist and are properly formatted"""
        # Convert spread from integer to decimal (divide by 1000 for most brokers)
        df['spread'] = df['spread'] / 1000

        # Calculate mid price
        df['price_mid'] = (df['bid'] + df['ask']) / 2

        # Calculate tick intervals
        df['tick_interval_ms'] = df['timestamp'].diff().dt.total_seconds() * 1000
        df['tick_interval_ms'] = df['tick_interval_ms'].fillna(0).clip(lower=0.1)  # Avoid division by zero

        # Calculate tick rate (ticks per second)
        df['tick_rate'] = 1000 / df['tick_interval_ms']
        df['tick_rate'] = df['tick_rate'].clip(upper=1000)  # Cap at 1000 ticks/sec

        return df

    def calculate_tick_microstructure_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate microstructure features at the tick level for predictive analytics.

        The logic is now *defensive*: if any of the key columns are missing
        (e.g. `bid`, `ask`, `spread`, or `price_mid`) we rebuild or safely
        default them so that downstream computations never fail with
        KeyError / AttributeError while still surfacing a meaningful signal.

        Parameters
        ----------
        df : pd.DataFrame
            Tick‑level dataframe, expected to contain at least one of:
            * 'price_mid'  – OR –  both 'bid' and 'ask'

        Returns
        -------
        pd.DataFrame
            Same dataframe with these extra columns appended/updated:
            * micro_return
            * volatility_5 / volatility_20
            * spread_z
            * tick_imbalance
        """
        # ------- Column sanity checks & auto‑reconstruction -------
        if 'price_mid' not in df.columns:
            if {'bid', 'ask'}.issubset(df.columns):
                df['price_mid'] = (df['bid'] + df['ask']) / 2
            else:
                raise ValueError(
                    "Input dataframe missing 'price_mid' and cannot derive it "
                    "because 'bid' / 'ask' are also absent."
                )

        # If spread is missing try to build it, otherwise fallback to zeros
        if 'spread' not in df.columns:
            if {'bid', 'ask'}.issubset(df.columns):
                df['spread'] = (df['ask'] - df['bid']).abs()
            else:
                df['spread'] = 0.0

        # Provide dummy bid / ask when absent so later imbalance calc is safe
        if 'bid' not in df.columns:
            df['bid'] = df['price_mid']
        if 'ask' not in df.columns:
            df['ask'] = df['price_mid']

        # ------- Feature engineering -------
        df['micro_return'] = df['price_mid'].pct_change().fillna(0)
        df['volatility_5'] = df['price_mid'].rolling(5).std().fillna(0)
        df['volatility_20'] = df['price_mid'].rolling(20).std().fillna(0)
        df['spread_z'] = (
            (df['spread'] - df['spread'].mean())
            / (df['spread'].std() + 1e-9)
        )
        df['tick_imbalance'] = (
            (df['bid'] - df['ask'])
            / (df['bid'] + df['ask'] + 1e-9)
        )

        return df

    def detect_mock_data(self, df: pd.DataFrame) -> Tuple[bool, Dict[str, float]]:
        """
        Heuristically decide whether the loaded tick data looks synthetic / mocked.

        Returns
        -------
        Tuple[bool, Dict[str, float]]
            * bool  -> True if the data is suspicious (likely mock)
            * dict  -> diagnostic metrics that triggered the suspicion
        """
        diagnostics: Dict[str, float] = {}

        # 1) Are price‑increments overly uniform?
        price_steps = df['price_mid'].diff().abs().round(8).dropna()
        diagnostics['unique_price_steps'] = price_steps.nunique()

        # 2) Is the spread almost always the same?
        diagnostics['unique_spread_values'] = df['spread'].nunique()

        # 3) Are tick intervals constant (i.e. generated on a timer)?
        diagnostics['tick_interval_std_ms'] = df['tick_interval_ms'].std()

        # 4) Make a simple judgement
        suspicious = (
            diagnostics['unique_price_steps'] < 3  # too few distinct price changes
            or diagnostics['unique_spread_values'] < 3  # spread doesn’t vary
            or diagnostics['tick_interval_std_ms'] < 1.0  # intervals virtually constant
        )

        return suspicious, diagnostics

    def infer_volume_from_ticks(self, df: pd.DataFrame) -> pd.DataFrame:
        """Infer volume using tick patterns, spread dynamics, and price movements"""
        params = self.config['analysis_modules']['volume_inference_engine']['params']

        # Feature engineering for volume inference
        df['price_change'] = df['price_mid'].diff().abs()
        df['spread_change'] = df['spread'].diff().abs()

        # Tick density (more ticks = higher volume)
        df['tick_density'] = df['tick_rate']

        # Spread dynamics (tighter spreads during high volume)
        df['spread_normalized'] = df['spread'] / df['price_mid']
        df['spread_volatility'] = df['spread_normalized'].rolling(20).std()

        # Price impact (larger moves = larger volume)
        df['price_velocity'] = df['price_change'] / (df['tick_interval_ms'] + 1)

        # Composite volume score with safe normalization
        features = ['tick_density', 'spread_change', 'price_velocity']
        df['volume_score'] = 0

        for feature, weight in zip(features, [params['tick_density_weight'],
                                             params['spread_change_weight'],
                                             params['price_movement_weight']]):
            if df[feature].std() > 0:
                normalized = (df[feature] - df[feature].mean()) / df[feature].std()
                df['volume_score'] += weight * normalized

        # Convert to actual volume estimate (normalized to reasonable range)
        df['inferred_volume'] = np.exp(df['volume_score'].clip(-3, 3)) * 100
        df['inferred_volume'] = df['inferred_volume'].fillna(100).clip(lower=0)

        return df

    def detect_icebergs(self, df: pd.DataFrame) -> List[Dict]:
        """Detect iceberg orders through repeated executions at similar price levels"""
        params = self.config['analysis_modules']['iceberg_detector']['params']
        iceberg_events = []

        df['price_rounded'] = ((df['bid'] + df['ask']) / 2).round(0)
        time_window = timedelta(seconds=params['time_window_seconds'])

        # Group by price levels and analyze execution patterns
        for price_level in df['price_rounded'].unique():
            level_data = df[df['price_rounded'] == price_level].copy()

            if len(level_data) >= params['min_executions']:
                # Check time clustering
                time_spread = level_data['timestamp'].max() - level_data['timestamp'].min()

                if time_spread <= time_window:
                    # Calculate execution pattern metrics
                    execution_intervals = level_data['timestamp'].diff().dt.total_seconds().dropna()

                    if len(execution_intervals) > 0 and execution_intervals.mean() > 0:
                        interval_consistency = 1 - (execution_intervals.std() / (execution_intervals.mean() + 1e-9))

                        if interval_consistency > 0.5:  # Consistent intervals suggest algorithmic execution
                            iceberg_events.append({
                                'type': 'iceberg_order',
                                'price_level': price_level,
                                'start_time': level_data['timestamp'].min(),
                                'end_time': level_data['timestamp'].max(),
                                'execution_count': len(level_data),
                                'avg_spread': level_data['spread'].mean(),
                                'interval_consistency': interval_consistency,
                                'estimated_total_size': len(level_data) * level_data['inferred_volume'].mean(),
                                'confidence': min(interval_consistency * (len(level_data) / params['min_executions']), 1.0)
                            })

        return iceberg_events

    def detect_spoofing(self, df: pd.DataFrame) -> List[Dict]:
        """Detect spoofing through spread manipulation patterns"""
        params = self.config['analysis_modules']['spoofing_detector']['params']
        spoofing_events = []

        df['spread_ma'] = df['spread'].rolling(20).mean()
        df['spread_spike'] = df['spread'] / (df['spread_ma'] + 1e-9)

        # Find spread spikes
        spike_mask = df['spread_spike'] > params['spread_spike_threshold']
        spike_indices = df[spike_mask].index

        for idx in spike_indices:
            if idx + 10 < len(df):  # Need future data to confirm reversal
                future_window = df.loc[idx:idx+10]

                # Check for quick reversal
                min_future_spread = future_window['spread'].min()
                reversal_ratio = min_future_spread / df.loc[idx, 'spread']

                if reversal_ratio < params['price_recovery_threshold']:
                    reversal_idx = future_window[future_window['spread'] == min_future_spread].index[0]
                    reversal_time = (df.loc[reversal_idx, 'timestamp'] -
                                   df.loc[idx, 'timestamp']).total_seconds() * 1000

                    if reversal_time < params['reversal_time_ms']:
                        spoofing_events.append({
                            'type': 'spoofing',
                            'timestamp': df.loc[idx, 'timestamp'],
                            'spike_spread': df.loc[idx, 'spread'],
                            'normal_spread': df.loc[idx, 'spread_ma'],
                            'spike_ratio': df.loc[idx, 'spread_spike'],
                            'reversal_time_ms': reversal_time,
                            'reversal_ratio': reversal_ratio,
                            'confidence': min((df.loc[idx, 'spread_spike'] - params['spread_spike_threshold']) / 2, 1.0)
                        })

        return spoofing_events

    def detect_quote_stuffing(self, df: pd.DataFrame) -> List[Dict]:
        """Detect quote stuffing through excessive update rates with minimal price movement"""
        params = self.config['analysis_modules']['quote_stuffing_detector']['params']
        stuffing_events = []

        # Calculate rolling metrics
        window_size = 50
        df['update_rate'] = df['tick_rate']
        df['price_movement'] = df['price_mid'].pct_change().abs()

        for i in range(window_size, len(df)):
            window = df.iloc[i-window_size:i]
            time_span = (window['timestamp'].iloc[-1] - window['timestamp'].iloc[0]).total_seconds()

            if time_span > 0:
                updates_per_second = len(window) / time_span
                avg_price_movement = window['price_movement'].mean()

                if (updates_per_second > params['update_rate_threshold'] and
                    avg_price_movement < params['price_movement_threshold']):

                    stuffing_events.append({
                        'type': 'quote_stuffing',
                        'start_time': window['timestamp'].iloc[0],
                        'end_time': window['timestamp'].iloc[-1],
                        'updates_per_second': updates_per_second,
                        'avg_price_movement': avg_price_movement,
                        'tick_count': len(window),
                        'confidence': min(updates_per_second / params['update_rate_threshold'] - 1, 1.0)
                    })

        return stuffing_events

    def detect_layering(self, df: pd.DataFrame) -> List[Dict]:
        """Detect layering through order book imbalance patterns"""
        params = self.config['analysis_modules']['layering_detector']['params']
        layering_events = []

        # Analyze bid-ask pressure
        df['bid_pressure'] = df['bid'].diff()
        df['ask_pressure'] = df['ask'].diff()
        df['pressure_imbalance'] = df['bid_pressure'] - df['ask_pressure']

        # Look for sustained one-sided pressure
        window = params['time_correlation_window']
        for i in range(window, len(df) - window):
            segment = df.iloc[i-window:i+window]

            # Check for consistent pressure in one direction
            if segment['pressure_imbalance'].std() > 0 and abs(segment['pressure_imbalance'].mean()) > segment['pressure_imbalance'].std() * 2:
                direction = 'buy' if segment['pressure_imbalance'].mean() > 0 else 'sell'

                layering_events.append({
                    'type': 'layering',
                    'timestamp': segment['timestamp'].iloc[len(segment)//2],
                    'direction': direction,
                    'pressure_imbalance': segment['pressure_imbalance'].mean(),
                    'consistency': 1 - (segment['pressure_imbalance'].std() / (abs(segment['pressure_imbalance'].mean()) + 1e-9)),
                    'affected_levels': len(segment['price_mid'].unique()),
                    'confidence': min(abs(segment['pressure_imbalance'].mean()) / segment['spread'].mean(), 1.0)
                })

        return layering_events

    def calculate_vpin(self, df: pd.DataFrame, bucket_size: int = 50) -> pd.DataFrame:
        """Calculate Volume-Synchronized Probability of Informed Trading (VPIN)"""
        df['price_direction'] = np.sign(df['price_mid'].diff())
        df['buy_volume'] = df['inferred_volume'] * (df['price_direction'] > 0)
        df['sell_volume'] = df['inferred_volume'] * (df['price_direction'] < 0)

        # Calculate VPIN in buckets
        vpin_values = []
        for i in range(bucket_size, len(df), bucket_size):
            bucket = df.iloc[i-bucket_size:i]
            total_volume = bucket['inferred_volume'].sum()
            if total_volume > 0:
                vpin = abs(bucket['buy_volume'].sum() - bucket['sell_volume'].sum()) / total_volume
            else:
                vpin = 0
            vpin_values.extend([vpin] * bucket_size)

        # Pad the end
        if len(vpin_values) < len(df):
            vpin_values.extend([vpin_values[-1] if vpin_values else 0] * (len(df) - len(vpin_values)))

        df['vpin'] = vpin_values[:len(df)]

        return df

    def detect_market_regime(self, df: pd.DataFrame) -> str:
        """Detect current market regime based on microstructure patterns"""
        # Calculate regime indicators
        spread_volatility = df['spread'].tail(100).std() / (df['spread'].mean() + 1e-9)
        tick_rate_variance = df['tick_interval_ms'].tail(100).var()
        price_volatility = df['price_mid'].tail(100).pct_change().std()
        avg_vpin = df['vpin'].tail(100).mean()

        # Regime classification
        if spread_volatility > 2 and tick_rate_variance > 10000:
            regime = 'breakdown'
        elif avg_vpin > 0.7 or len(self.session_state['spoofing_events']) > 5:
            regime = 'manipulated'
        elif price_volatility > df['price_mid'].pct_change().std() * 2:
            regime = 'stressed'
        else:
            regime = 'normal'

        return regime

    # ---------- Predictive Setup Scanner & Enhanced Visualisations ----------
    def create_predictive_signals(self, df: pd.DataFrame) -> Dict:
        """Generate predictive trading signals from tick microstructure"""
        signals: Dict[str, List] = {
            'reversal_setups': [],
            'breakout_setups': [],
            'trap_setups': [],
        }

        # Pre‑compute helper columns (safe guards for missing cols)
        if 'order_flow_imbalance' not in df.columns and 'bid_pressure' in df.columns:
            df['order_flow_imbalance'] = (df['bid_pressure'] - df['ask_pressure']).rolling(50).mean()

        df['tick_reversal_score'] = (
            df['order_flow_imbalance'].rolling(20).std().fillna(0) *
            df['vpin'].rolling(20).mean().fillna(0)
        )

        df['volume_acceleration'] = df['inferred_volume'].diff().rolling(10).mean().fillna(0)
        df['breakout_score'] = df['volume_acceleration'] / (df['spread'].rolling(20).mean().fillna(1e-9) + 1e-9)

        # Scan last 300 ticks (or full df if smaller)
        lookback = min(300, len(df))
        for i in range(50, lookback):
            window = df.iloc[i-50:i]

            # Reversal
            if window['tick_reversal_score'].iloc[-1] > window['tick_reversal_score'].quantile(0.9):
                direction = 'long' if window['order_flow_imbalance'].iloc[-1] < 0 else 'short'
                signals['reversal_setups'].append({
                    'timestamp': window['timestamp'].iloc[-1],
                    'price': window['price_mid'].iloc[-1],
                    'direction': direction,
                    'confidence': float(min(window['tick_reversal_score'].iloc[-1] / 2, 1.0)),
                })

            # Break‑out
            if window['breakout_score'].iloc[-1] > window['breakout_score'].quantile(0.95):
                signals['breakout_setups'].append({
                    'timestamp': window['timestamp'].iloc[-1],
                    'price': window['price_mid'].iloc[-1],
                    'target': window['price_mid'].iloc[-1] + (window['price_mid'].std() * 2),
                    'confidence': float(min(window['breakout_score'].iloc[-1] / 5, 1.0)),
                })

        return signals

    def render_predictive_scanner(self, df: pd.DataFrame, signals: Dict) -> None:
        """Render predictive scanner panels"""
        import plotly.graph_objects as go
        col1, col2 = st.columns(2)

        # --- Reversal setups plot ---
        with col1:
            st.markdown("##### 🔄 Reversal Setups")
            if signals['reversal_setups']:
                fig_rev = go.Figure()
                # price trace
                fig_rev.add_trace(go.Scatter(
                    x=df['timestamp'], y=df['price_mid'],
                    mode='lines', name='Price', line=dict(color='gray', width=1)
                ))
                rev_df = pd.DataFrame(signals['reversal_setups'])
                for direction, colour, sym in [('long', 'green', 'triangle-up'), ('short', 'red', 'triangle-down')]:
                    dir_df = rev_df[rev_df['direction'] == direction]
                    if not dir_df.empty:
                        fig_rev.add_trace(go.Scatter(
                            x=dir_df['timestamp'], y=dir_df['price'],
                            mode='markers', name=f"{direction.capitalize()}",
                            marker=dict(symbol=sym, size=10, color=colour,
                                        opacity=dir_df['confidence'])
                        ))
                fig_rev.update_layout(showlegend=True, height=300)
                st.plotly_chart(fig_rev, use_container_width=True)
            else:
                st.info("No reversal setups flagged in look‑back window.")

        # --- Setup metrics ---
        with col2:
            st.markdown("##### 📊 Setup Metrics")
            tot_rev = len(signals['reversal_setups'])
            tot_bo  = len(signals['breakout_setups'])
            hi_conf = sum(1 for s in signals['reversal_setups'] if s['confidence'] > 0.7)
            m1, m2, m3 = st.columns(3)
            m1.metric("Reversals", tot_rev)
            m2.metric("Break‑outs", tot_bo)
            m3.metric("High‑conf", hi_conf)

    # ---------- Layering & Quote‑stuffing tabs ----------
    def render_layering_tab(self, layering_events: List[Dict]) -> None:
        if layering_events:
            layer_df = pd.DataFrame(layering_events)
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=layer_df['timestamp'], y=layer_df['pressure_imbalance'],
                mode='markers',
                marker=dict(size=layer_df['affected_levels']*5,
                            color=layer_df['confidence'], colorscale='RdBu',
                            showscale=True),
                text=layer_df['direction'],
                name='Layering'
            ))
            fig.update_layout(title="Layering Pressure Analysis",
                              xaxis_title="Time", yaxis_title="Pressure Imbalance")
            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(layer_df[['timestamp', 'direction',
                                   'pressure_imbalance',
                                   'affected_levels',
                                   'confidence']].round(3))
        else:
            st.info("No layering events detected.")

    def render_quote_stuffing_tab(self, stuffing_events: List[Dict]) -> None:
        if stuffing_events:
            q_df = pd.DataFrame(stuffing_events)
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=q_df['start_time'], y=q_df['updates_per_second'],
                mode='markers',
                marker=dict(size=q_df['tick_count']/10,
                            color=q_df['confidence'],
                            colorscale='Hot', showscale=True),
                name='Stuffing intensity'
            ))
            fig.update_layout(title="Quote Stuffing Intensity Map",
                              xaxis_title="Time", yaxis_title="Updates / s")
            st.plotly_chart(fig, use_container_width=True)
            c1, c2, c3 = st.columns(3)
            c1.metric("Total events", len(q_df))
            c2.metric("Max rate", f"{q_df['updates_per_second'].max():.0f}/s")
            avg_dur = (q_df['end_time'] - q_df['start_time']).dt.total_seconds().mean()
            c3.metric("Avg duration", f"{avg_dur:.1f}s")
            st.dataframe(q_df[['start_time', 'updates_per_second',
                               'avg_price_movement', 'tick_count',
                               'confidence']].round(4))
        else:
            st.info("No quote‑stuffing events detected.")

    def create_advanced_dashboard(self, df: pd.DataFrame, selected_file: str):
        """Create comprehensive dashboard with all advanced analytics (each chart as its own figure)"""

        # QRTDeskAnalytics instance for advanced microstructure analytics
        qrt = QRTDeskAnalytics()
        qrt.session_state = self.session_state

        # Header
        st.title("🧬 Quantum Microstructure Analysis System")
        with st.expander("🧠 Why Tick Charts Matter (Scalping Microstructure Commentary)", expanded=False):
            st.markdown(
                """
**As a predictive trade researcher**, tick charts are a foundational tool for scalping engineered liquidity and identifying traps with precision.

### 🎯 Tick Charts for Scalping: The Granular Edge

Tick charts produce bars based on the number of trades, not time. This enables:
- **Micro-Level Resolution**: Real-time view of supply/demand shifts.
- **Noise Reduction**: Only prints bars during active participation.
- **Real-Time Volatility**: Bar speed shows instant momentum.
- **Pinpoint Precision**: Ideal for SL/TP placement in tight-range trades.

### 🧬 Tick-M1-HTF Confluence with ZANFLOW

- **Micro-Wyckoff Events**: Tick-based Spring/Upthrusts with volume spikes and fast rejections.
- **Inducement & Engineered Liquidity**: Sweeps + snapbacks at POIs visible only at tick granularity.
- **Pre-Confirmation Traps**: Tick reversal score flags setups before M1/M5 confirmation.
- **Multi-Timeframe Context**: Tick ➝ M1/M5 ➝ H1/H4 bias from ContextAnalyzer ensures alignment.

### 🔁 Volume, FVGs & SL/TP Orchestration

- **Volume Delta** confirms imbalance aggression.
- **FVGs & Order Blocks** as re-entry zones post-CHoCH.
- **ATR + structural anchors** guide adaptive stop loss.
- **POC + liquidity pools** guide high-R:R take profits.

For implementation logic, refer to:
- `Scalp_Inducement_Reversal_HTF_Confluence` agent profile YAML (conceptual).
- Modules: `LiquidityEngine`, `RiskManager`, `PredictiveScorer`, `ConfluenceStacker`.
"""
            )
        asset = selected_file.split('_')[0] if '_' in selected_file else 'Unknown'
        st.caption(f"Asset: {asset} | File: {selected_file} | Regime: {self.session_state['market_regime'].upper()}")

        # ——— Research Commentary ———
        with st.expander("📚 Research Commentary (methodology & caveats)", expanded=False):
            st.markdown(
                """
**MetaTrader data caveat:**  
We analyse `<TICKVOL>` and `<SPREAD>` from MetaTrader exports. These lack true Level II order-book depth, so Quote-Stuffing and Spoofing signals are **heuristic** rather than definitive.

**ZANFLOW microstructure heuristics**

| Signal | What we look for in tick data | Heuristic trigger |
| --- | --- | --- |
| **Quote Stuffing Density** | Extreme burst of tick updates with <1 bp price change | `updates / sec` > threshold **and** `avg_price_movement` below threshold |
| **Spoofing Patterns** | Spread spikes that reverse within ≤ 250 ms plus no follow-through in price | `spread_spike` > 3×MA **then** quick reversion |
| **Regime Transitions** | VPIN > 0.7 ⇒ *manipulated* • VPIN 0.5-0.7 ⇒ *stressed* • else *normal* | VPIN 100-tick rolling |

**Further reading**

* [Early Market Signals and Confirmations](sandbox:/mnt/data/Early Market Signals and Confirmations.md)  
* [Market Trading Techniques and Anomalies](sandbox:/mnt/data/Market Trading Techniques and Anomalies.md)  
* [Trap Reversal Tick-Validated JSON](sandbox:/mnt/data/SMC_EngineeredLiquidity_TrapReversal_TickValidated_v12.json)  
* [Tick Data Analysis Notes](sandbox:/mnt/data/tick_data_analisys.json)

These documents expand on engineered-liquidity traps, Wyckoff sweeps, and the VPIN-driven regime model used here.
"""
            )

        # Key Metrics Row
        col1, col2, col3, col4, col5, col6 = st.columns(6)
        col1.metric("Iceberg Orders", len(self.session_state['iceberg_events']))
        col2.metric("Spoofing Events", len(self.session_state['spoofing_events']))
        col3.metric("Manipulation Score", f"{self.session_state['manipulation_score']:.2f}")
        col4.metric("Avg VPIN", f"{df['vpin'].mean():.3f}")
        col5.metric("Toxic Flow %", f"{len(self.session_state['toxic_flow_periods'])/len(df)*100:.1f}%")
        col6.metric("Hidden Liquidity", len(self.session_state['hidden_liquidity_map']))
        # --- Realtime regime alert ---
        self.check_regime_alerts(self.session_state['market_regime'], df)

        # 1. Price & Inferred Volume
        try:
            fig1 = go.Figure()
            fig1.add_trace(go.Scatter(x=df['timestamp'], y=df['price_mid'], name='Price', line=dict(color='#1f77b4')))
            fig1.add_trace(go.Bar(x=df['timestamp'], y=df['inferred_volume'], name='Volume', marker=dict(color='#ff7f0e', opacity=0.3)))
            fig1.update_layout(title="Price & Inferred Volume", xaxis_title="Time", yaxis_title="Price / Volume", showlegend=True)
            st.plotly_chart(fig1, use_container_width=True)
            st.caption("Price vs Inferred Volume: Shows the evolution of market price alongside estimated trading volume. The line represents price, and the bars represent inferred volume at each tick.")
            # Dynamic commentary
            price_change = df['price_mid'].iloc[-1] - df['price_mid'].iloc[0]
            total_vol = df['inferred_volume'].sum()
            st.markdown(f"**Quick take:** Price moved {price_change:+.4f} points over the displayed period with an estimated {total_vol:,.0f} units traded.")
        except Exception:
            pass

        # 2. Spread Dynamics & Anomalies
        try:
            fig2 = go.Figure()
            fig2.add_trace(go.Scatter(x=df['timestamp'], y=df['spread'], name='Spread', line=dict(color='#2ca02c')))
            # Add spoofing markers
            for event in self.session_state['spoofing_events']:
                fig2.add_trace(
                    go.Scatter(
                        x=[event['timestamp']], y=[event['spike_spread']],
                        mode='markers', marker=dict(color='red', size=10, symbol='x'),
                        name='Spoofing', showlegend=False
                    )
                )
            fig2.update_layout(title="Spread Dynamics & Anomalies", xaxis_title="Time", yaxis_title="Spread", showlegend=True)
            st.plotly_chart(fig2, use_container_width=True)
            st.caption("Spread Dynamics & Anomalies: Visualizes spread changes over time and highlights detected spoofing events with red X markers.")
            # Dynamic commentary
            avg_spread = df['spread'].mean()
            st.markdown(f"**Spread check:** Average spread {avg_spread:.4f} • Spoofing spikes detected: {len(self.session_state['spoofing_events'])}.")
        except Exception:
            pass

        # 3. Tick Rate Heatmap
        try:
            fig3 = go.Figure()
            heatmap = go.Histogram2d(
                x=df['timestamp'],
                y=df['tick_rate'],
                colorscale='Hot',
                nbinsx=100,
                nbinsy=50
            )
            fig3.add_trace(heatmap)
            fig3.update_layout(title="Tick Rate Heatmap", xaxis_title="Time", yaxis_title="Tick Rate")
            st.plotly_chart(fig3, use_container_width=True)
            st.caption("Tick Rate Heatmap: Displays the density of tick updates over time and tick rate. Brighter areas indicate higher density of updates.")
            # Dynamic commentary
            peak_tick_rate = df['tick_rate'].max()
            st.markdown(f"**Note:** Peak tick rate hit {peak_tick_rate:.1f} updates / sec in this window.")
        except Exception:
            pass

        # 4. VPIN (Toxicity)
        try:
            fig4 = go.Figure()
            fig4.add_trace(go.Scatter(x=df['timestamp'], y=df['vpin'], name='VPIN', line=dict(color='#d62728')))
            fig4.add_hline(y=0.5, line_dash="dash", line_color="gray")
            fig4.update_layout(title="VPIN (Toxicity)", xaxis_title="Time", yaxis_title="VPIN", showlegend=True)
            st.plotly_chart(fig4, use_container_width=True)
            st.caption("VPIN (Toxicity): Quantifies order flow toxicity and potential for informed trading. High VPIN values (above 0.5) may indicate toxic, informed, or predatory trading.")
            # Dynamic commentary
            toxic_pct = (df['vpin'] > 0.5).mean() * 100
            st.markdown(f"**Flow toxicity:** {toxic_pct:.1f}% of ticks flagged as high‑risk (VPIN > 0.5).")
        except Exception:
            pass

        # 5. Manipulation Timeline
        try:
            all_events = (
                [{'time': e['timestamp'], 'type': e['type'], 'conf': e['confidence']} for e in self.session_state['spoofing_events']] +
                [{'time': e['start_time'], 'type': e['type'], 'conf': e['confidence']} for e in self.session_state['iceberg_events']]
            )
            if all_events:
                event_df = pd.DataFrame(all_events)
                fig5 = go.Figure()
                for event_type in event_df['type'].unique():
                    type_events = event_df[event_df['type'] == event_type]
                    fig5.add_trace(
                        go.Scatter(
                            x=type_events['time'], y=type_events['conf'],
                            mode='markers', name=event_type,
                            marker=dict(size=10)
                        )
                    )
                fig5.update_layout(title="Manipulation Timeline", xaxis_title="Time", yaxis_title="Confidence", showlegend=True)
                st.plotly_chart(fig5, use_container_width=True)
                st.caption("Manipulation Timeline: Plots the timing and confidence of detected spoofing and iceberg events. Each marker represents a detected event, with its confidence score.")
                # Dynamic commentary
                st.markdown(f"**Summary:** {len(self.session_state['spoofing_events'])} spoofing and {len(self.session_state['iceberg_events'])} iceberg events recorded in view.")
        except Exception:
            pass

        # 6. Iceberg Detection Map
        try:
            if self.session_state['iceberg_events']:
                iceberg_df = pd.DataFrame(self.session_state['iceberg_events'])
                fig6 = go.Figure()
                fig6.add_trace(
                    go.Scatter(
                        x=iceberg_df['start_time'],
                        y=iceberg_df['price_level'],
                        mode='markers',
                        marker=dict(
                            size=iceberg_df['estimated_total_size']/100,
                            color=iceberg_df['confidence'],
                            colorscale='Viridis',
                            showscale=True
                        ),
                        text=[f"Size: {s:.0f}" for s in iceberg_df['estimated_total_size']],
                        name='Icebergs'
                    )
                )
                fig6.update_layout(title="Iceberg Detection Map", xaxis_title="Time", yaxis_title="Price Level", showlegend=False)
                st.plotly_chart(fig6, use_container_width=True)
                st.caption("Iceberg Detection Map: Shows locations and confidence of detected iceberg orders. Marker size is proportional to estimated order size; color indicates detection confidence.")
                # Dynamic commentary
                total_iceberg_vol = iceberg_df['estimated_total_size'].sum()
                st.markdown(f"**Aggregate:** Total inferred iceberg volume ≈ {total_iceberg_vol:,.0f} units.")
        except Exception:
            pass

        # 7. Order Flow Imbalance
        try:
            if 'bid_pressure' in df.columns and 'ask_pressure' in df.columns:
                df['order_flow_imbalance'] = (df['bid_pressure'] - df['ask_pressure']).rolling(50).mean()
                fig7 = go.Figure()
                fig7.add_trace(
                    go.Scatter(
                        x=df['timestamp'],
                        y=df['order_flow_imbalance'],
                        name='Order Flow Imbalance',
                        fill='tozeroy',
                        line=dict(color='#9467bd')
                    )
                )
                fig7.update_layout(title="Order Flow Imbalance", xaxis_title="Time", yaxis_title="Imbalance", showlegend=True)
                st.plotly_chart(fig7, use_container_width=True)
                st.caption("Order Flow Imbalance: Indicates the net pressure from bids vs. asks over time. Positive values suggest buying pressure; negative values indicate selling pressure.")
                # Dynamic commentary
                peak_imb = df['order_flow_imbalance'].abs().max()
                st.markdown(f"**Highlight:** Max absolute imbalance reached {peak_imb:.2f}.")
        except Exception:
            pass

        # 8. Microstructure 3D Surface
        try:
            time_bins = pd.cut(df.index, bins=50, labels=False)
            price_bins = pd.cut(df['price_mid'], bins=50, labels=False)
            surface_data = pd.pivot_table(
                df, values='inferred_volume',
                index=price_bins, columns=time_bins,
                aggfunc='sum', fill_value=0
            )
            if not surface_data.empty:
                fig8 = go.Figure()
                fig8.add_trace(
                    go.Surface(
                        z=surface_data.values,
                        colorscale='Viridis',
                        name='Volume Surface'
                    )
                )
                fig8.update_layout(title="Microstructure 3D Surface", scene=dict(
                    xaxis_title="Time Bin",
                    yaxis_title="Price Bin",
                    zaxis_title="Volume"
                ))
                st.plotly_chart(fig8, use_container_width=True)
                st.caption("Microstructure 3D Surface: 3D visualization of volume distribution across price and time. Peaks indicate where large volumes concentrate in the price-time grid.")
                # Dynamic commentary
                st.markdown("**Interpretation:** Volume peaks mark hotspots where large orders clustered at specific price‑time zones.")
        except Exception:
            pass

        # 9. Hidden Liquidity Zones
        try:
            support_levels = df.groupby(df['price_mid'].round(0))['inferred_volume'].sum().sort_values(ascending=False).head(10)
            if not support_levels.empty:
                fig9 = go.Figure()
                fig9.add_trace(
                    go.Bar(
                        x=support_levels.values,
                        y=support_levels.index,
                        orientation='h',
                        name='Hidden Liquidity',
                        marker=dict(color='#8c564b')
                    )
                )
                fig9.update_layout(title="Hidden Liquidity Zones", xaxis_title="Inferred Volume", yaxis_title="Price Level", showlegend=False)
                st.plotly_chart(fig9, use_container_width=True)
                st.caption("Hidden Liquidity Zones: Highlights price levels with concentrated inferred volume. Bars show the top 10 price levels where large hidden orders may reside.")
                # Dynamic commentary
                top_level = support_levels.index[0]
                top_vol = support_levels.iloc[0]
                st.markdown(f"**Takeaway:** Level {top_level:.2f} holds the densest hidden liquidity (~{top_vol:,.0f} units).")
        except Exception:
            pass

        # 10. Quote Stuffing Density
        try:
            st.markdown("#### Quote Stuffing Density")
            if self.session_state.get('quote_stuffing_events'):
                qs_df = pd.DataFrame(self.session_state['quote_stuffing_events'])
                qs_df['duration_s'] = (qs_df['end_time'] - qs_df['start_time']).dt.total_seconds()
                fig_qs = go.Figure()
                fig_qs.add_trace(go.Bar(
                    x=qs_df['start_time'],
                    y=qs_df['updates_per_second'],
                    name='Updates / s',
                    marker=dict(color='#e377c2')
                ))
                fig_qs.update_layout(title="Quote Stuffing Density",
                                     xaxis_title="Time",
                                     yaxis_title="Updates per Second")
                st.plotly_chart(fig_qs, use_container_width=True)
                st.caption("Quote Stuffing Density: Bars represent detected stuffing periods; height indicates quote‑update rate during each burst.")
                # Dynamic commentary
                max_rate = qs_df['updates_per_second'].max()
                st.markdown(f"**Observation:** Highest burst reached {max_rate:.1f} quotes / sec across {len(qs_df)} stuffing episodes.")
            else:
                st.info("No quote stuffing episodes detected.")
        except Exception:
            pass

        # 11. Spoofing Patterns
        try:
            st.markdown("#### Spoofing Patterns")
            if self.session_state['spoofing_events']:
                sp_df = pd.DataFrame(self.session_state['spoofing_events'])
                sp_df['minute'] = sp_df['timestamp'].dt.floor('min')
                counts = sp_df.groupby('minute').size()
                fig_sp = go.Figure()
                fig_sp.add_trace(go.Bar(
                    x=counts.index,
                    y=counts.values,

                    name='Spoofing Events',
                    marker=dict(color='#17becf')
                ))
                fig_sp.update_layout(title="Spoofing Pattern Frequency",
                                     xaxis_title="Minute",
                                     yaxis_title="Number of Spoofing Events")
                st.plotly_chart(fig_sp, use_container_width=True)
                st.caption("Spoofing Patterns: Bars show how many spoofing spikes occurred in each minute.")
                # Dynamic commentary
                total_spoof = len(self.session_state['spoofing_events'])
                peak_minute = counts.max() if not counts.empty else 0
                st.markdown(f"**Insight:** {total_spoof} spoofing events total; busiest minute saw {peak_minute} events.")
            else:
                st.info("No spoofing events detected.")
        except Exception:
            pass

        # 12. Regime Transitions
        try:
            st.markdown("#### Regime Transitions")
            # Simple regime classification based on VPIN thresholds
            df['regime_simple'] = np.where(df['vpin'] > 0.7, 'manipulated',
                                   np.where(df['vpin'] > 0.5, 'stressed', 'normal'))
            regime_map = {'normal': 0, 'stressed': 1, 'manipulated': 2}
            df['regime_code'] = df['regime_simple'].map(regime_map)
            fig_reg = go.Figure()
            fig_reg.add_trace(go.Scatter(
                x=df['timestamp'],
                y=df['regime_code'],
                mode='lines',
                line=dict(shape='hv'),
                name='Regime'
            ))
            fig_reg.update_layout(
                title="Regime Transitions",
                xaxis_title="Time",
                yaxis=dict(
                    tickmode='array',
                    tickvals=list(regime_map.values()),
                    ticktext=list(regime_map.keys())
                ),
                showlegend=False
            )
            st.plotly_chart(fig_reg, use_container_width=True)
            st.caption("Regime Transitions: The step‑line shows shifts between market regimes derived from VPIN thresholds (>0.7 = manipulated, >0.5 = stressed, else normal).")
            # Dynamic commentary
            regime_counts = df['regime_simple'].value_counts(normalize=True) * 100
            breakdown = ", ".join([f"{k}: {v:.1f}%" for k, v in regime_counts.items()])
            st.markdown(f"**Breakdown:** {breakdown}")
        except Exception:
            pass

        # 13. Liquidity Sweep Detection (enhanced)
        st.markdown("#### Liquidity Sweep Detection")
        sweep_results = qrt.detect_liquidity_sweeps_enhanced(df)
        st.write(
            f"Detected {sweep_results['count']} sweeps "
            f"(stop‑hunts = {sweep_results['stop_hunts']}, "
            f"liquidity‑grabs = {sweep_results['liquidity_grabs']})."
        )

        if sweep_results['sweep_events']:
            self.create_liquidity_sweep_visualization(df, sweep_results['sweep_events'])
        else:
            st.info("No major liquidity sweeps detected in this window.")

        # 14. Execution Quality Metrics
        st.markdown("#### Execution Quality Metrics")
        exec_metrics = qrt.compute_execution_quality_metrics(df)
        col1, col2, col3, col4 = st.columns(4)

        col1.metric(
            "Avg Spread (bps)",
            f"{exec_metrics.get('avg_spread_bps', 0):.1f}",
            help="Average spread in basis points"
        )

        col2.metric(
            "Adverse Selection",
            f"{exec_metrics.get('adverse_selection_score', 1.0):.2f}",
            help="Higher = more adverse selection risk"
        )

        col3.metric(
            "Price Impact (λ)",
            f"{exec_metrics.get('kyle_lambda', 0):.4f}",
            help="Kyle's lambda - price impact per unit volume"
        )

        col4.metric(
            "Exec Favorability",
            f"{exec_metrics.get('current_exec_favorability', 0.5):.1%}",
            help="Current execution conditions (0-100%)"
        )

        # 15. Killzone Analysis
        st.markdown("#### Killzone Analysis")
        killzone_results = qrt.identify_killzone_patterns(df)
        st.write(f"Detected {killzone_results['count']} killzone events.")
        if killzone_results['killzone_events']:
            kz_df = pd.DataFrame(killzone_results['killzone_events'])
            st.dataframe(kz_df)
        else:
            st.info("No killzone patterns detected in this window.")

        # 16. Predictive Setup Scanner
        st.markdown("#### Predictive Setup Scanner")
        df_pred = self.calculate_tick_microstructure_features(df)
        signals = self.create_predictive_signals(df_pred)
        self.render_predictive_scanner(df_pred, signals)

        # Detailed Analysis Sections (unchanged)
        with st.expander("🔍 Manipulation Event Details", expanded=True):
            tab1, tab2, tab3, tab4 = st.tabs(["Icebergs", "Spoofing", "Layering", "Quote Stuffing"])

            with tab1:
                if self.session_state['iceberg_events']:
                    iceberg_df = pd.DataFrame(self.session_state['iceberg_events'])
                    st.dataframe(iceberg_df[['price_level', 'start_time', 'execution_count',
                                           'estimated_total_size', 'confidence']].round(2))
                else:
                    st.info("No iceberg orders detected")

            with tab2:
                if self.session_state['spoofing_events']:
                    spoof_df = pd.DataFrame(self.session_state['spoofing_events'])
                    st.dataframe(spoof_df[['timestamp', 'spike_spread', 'normal_spread',
                                         'reversal_time_ms', 'confidence']].round(2))
                else:
                    st.info("No spoofing events detected")

            with tab3:
                layering_events = self.detect_layering(df)
                self.render_layering_tab(layering_events)

            with tab4:
                self.render_quote_stuffing_tab(self.session_state.get('quote_stuffing_events', []))

        # Market Quality Metrics (unchanged)
        with st.expander("📊 Market Quality Metrics"):
            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric("Avg Spread", f"{df['spread'].mean():.4f}")
                st.metric("Spread Volatility", f"{df['spread'].std():.4f}")
                st.metric("Price Efficiency", f"{1 - df['spread'].mean()/df['price_mid'].mean():.6f}")

            with col2:
                st.metric("Avg Tick Rate", f"{df['tick_rate'].mean():.1f}/s")
                st.metric("Max Tick Burst", f"{df['tick_rate'].max():.0f}/s")
                st.metric("Tick Clustering", f"{df['tick_interval_ms'].std()/df['tick_interval_ms'].mean():.2f}")

            with col3:
                st.metric("Inferred Volume", f"{df['inferred_volume'].sum():,.0f}")
                st.metric("Volume Concentration", f"{df['inferred_volume'].std()/df['inferred_volume'].mean():.2f}")
                st.metric("Price Impact", f"{df['price_velocity'].mean():.8f}")

# Main execution
if __name__ == "__main__":
    st.sidebar.title("🧬 Quantum Configuration")

    # --- Resolve data folder from Streamlit secrets first, then fallback to .streamlit/secrets.toml ---
    try:
        # Primary: Streamlit-cloud style secrets
        tick_files_directory = st.secrets["raw_data_directory"]
        st.sidebar.success(f"Data Source:\n{tick_files_directory}")
    except Exception:
        # Local fallback: .streamlit/secrets.toml at project root
        script_dir = os.path.dirname(__file__)
        project_root = os.path.abspath(os.path.join(script_dir, os.pardir))
        secrets_path = os.path.join(project_root, ".streamlit", "secrets.toml")

        if os.path.exists(secrets_path):
            import toml  # local import only if needed

            secrets = toml.load(secrets_path)
            tick_files_directory = secrets.get("raw_data_directory", "")
            if tick_files_directory:
                st.sidebar.success(f"Data Source:\n{tick_files_directory}")
            else:
                st.sidebar.error("`raw_data_directory` not found in .streamlit/secrets.toml")
                st.stop()
        else:
            st.sidebar.error("No Streamlit secrets available and fallback .streamlit/secrets.toml not found.")
            st.stop()

    # FIXED: Only show files with "ticks" in the name
    valid_files = [f for f in os.listdir(tick_files_directory)
                   if 'ticks' in f.lower() and f.endswith(('.csv', '.txt')) and not f.startswith('._')]

    if not valid_files:
        st.sidebar.error("No tick files found")
        st.stop()

    selected_file = st.sidebar.selectbox("Select Tick Data", sorted(valid_files))
    file_path = os.path.join(tick_files_directory, selected_file)
    # DEBUG: show the resolved file path so we know exactly which file is being ingested
    st.sidebar.info(f"📂 Reading tick file: {file_path}")

    # Advanced options
    st.sidebar.markdown("### Advanced Settings")
    sensitivity = st.sidebar.slider("Detection Sensitivity", 0.5, 2.0, 1.0, 0.1)

    # Initialize analyzer
    script_dir = os.path.dirname(__file__)
    config_path = os.path.join(script_dir, 'quantum_microstructure_config.yaml')

    # Load OpenAI API key from st.secrets (already imported above)

    analyzer = QuantumMicrostructureAnalyzer(config_path)

    # Load and analyze data
    with st.spinner("🧬 Running quantum analysis..."):
        # Now ingesting standard comma‑separated CSV files
        df = pd.read_csv(file_path, encoding_errors='ignore')  # default sep=','
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        # Ensure data is in chronological order (oldest → newest) so all rolling/diff
        # calculations operate on the most‑recent bars instead of the earliest ones.
        df = df.sort_values('timestamp').reset_index(drop=True)
        # DEBUG: quick peek at the data to verify timestamps and latest candles
        with st.expander("🔎 Data preview (head & tail)", expanded=False):
            st.write("Head of data:")
            st.write(df.head())
            st.write("Tail of data:")
            st.write(df.tail())
        max_bars = st.sidebar.slider("Bars to Display", 50, len(df), min(1000, len(df)))
        df = df.tail(max_bars)
        st.caption(
            "This dashboard visualizes real-time tick data with derived microstructure metrics. Use it to detect spoofing, iceberg orders, quote stuffing, and assess trading toxicity via VPIN.")

        # FIXED: Preprocess data to ensure all columns exist
        df = analyzer.preprocess_data(df)

        # Heuristic sanity‑check: does this look like real tick data?
        is_mock, diag = analyzer.detect_mock_data(df)
        if is_mock:
            st.warning(
                "⚠️  The loaded file exhibits characteristics of synthetic/mock data. "
                f"Diagnostics: {diag}"
            )

        # Core analysis pipeline
        # Additional ZANFLOW pipeline integration point (ISPTS Instant Reversion Logic can hook here)
        df = analyzer.infer_volume_from_ticks(df)
        df = analyzer.calculate_vpin(df)

        # Detect all manipulation patterns
        analyzer.session_state['iceberg_events'] = analyzer.detect_icebergs(df)
        analyzer.session_state['spoofing_events'] = analyzer.detect_spoofing(df)
        quote_stuffing = analyzer.detect_quote_stuffing(df)
        analyzer.session_state['quote_stuffing_events'] = quote_stuffing
        layering = analyzer.detect_layering(df)

        # Calculate manipulation score
        total_events = (len(analyzer.session_state['iceberg_events']) +
                       len(analyzer.session_state['spoofing_events']) +
                       len(quote_stuffing) + len(layering))
        analyzer.session_state['manipulation_score'] = min(total_events / 10, 10)

        # Detect toxic flow periods
        analyzer.session_state['toxic_flow_periods'] = df[df['vpin'] > 0.7].index.tolist()

        # Detect market regime
        analyzer.session_state['market_regime'] = analyzer.detect_market_regime(df)

        # ---- Vectorizer Integration ----
        if 'vector_state' not in st.session_state:
            st.session_state.vector_state = {
                'last_vectorized_idx': 0,
                'total_vectors': 0,
                'anomaly_count': 0
            }

        vectorizer_config = {
            'tick_vectorizer': {
                'embedding_dim': 1536,
                'feature_extractors': ['microstructure', 'regime', 'temporal']
            }
        }

        tick_vectorizer = TickVectorizer(vectorizer_config)
        vector_dashboard = VectorizedDashboard(tick_vectorizer)
        st.session_state.vector_state = vector_dashboard.update_tick_vectors(df, st.session_state.vector_state)

        with st.expander("🧬 Tick Vector Analysis", expanded=True):
            vector_dashboard.render_vector_analytics(st)

        # Create dashboard
        analyzer.create_advanced_dashboard(df, selected_file)

    # Add session state to sidebar
    with st.sidebar.expander("Session State"):
        st.json({
            'total_ticks': len(df),
            'regime': analyzer.session_state['market_regime'],
            'manipulation_score': round(analyzer.session_state['manipulation_score'], 2),
            'events_detected': total_events
        })
# Placeholder functions for referenced visualizations
def create_liquidity_sweep_heatmap(sweep_df):
    import streamlit as st
    st.caption("Liquidity sweep heatmap placeholder (implement visualization here).")

def create_predictive_signals(df):
    import streamlit as st
    st.caption("Predictive signals scanner placeholder (implement visualization here).")
    import json
    from datetime import datetime
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table
    from reportlab.lib.styles import getSampleStyleSheet

    def setup_realtime_alerts(self):
        self.last_regime = None
        self.alert_queue = []

    def check_regime_alerts(self, current_regime: str, df: pd.DataFrame):
        if hasattr(self, 'last_regime') and self.last_regime and current_regime != self.last_regime:
            alert = {
                'type': 'regime_change',
                'from': self.last_regime,
                'to': current_regime,
                'timestamp': df['timestamp'].iloc[-1],
                'vpin': df['vpin'].iloc[-1],
                'confidence': 0.9
            }
            st.toast(f"⚠️ Regime Change: {self.last_regime} → {current_regime}", icon='🔄')
            with st.sidebar:
                st.error(f"REGIME ALERT: Now in {current_regime.upper()} regime")
            if hasattr(self, 'alert_queue'):
                self.alert_queue.append(alert)
        self.last_regime = current_regime

    def create_pattern_snapshot(self, df: pd.DataFrame, events: dict) -> dict:
        snapshot = {
            'metadata': {
                'timestamp': datetime.now().isoformat(),
                'symbol': getattr(self, 'current_symbol', 'Unknown'),
                'tick_count': len(df),
                'regime': self.session_state.get('market_regime', 'unknown')
            },
            'events': events,
            'statistics': {
                'manipulation_score': self.session_state.get('manipulation_score', 0),
                'avg_vpin': df['vpin'].mean(),
                'regime_distribution': df['regime_simple'].value_counts().to_dict() if 'regime_simple' in df else {}
            }
        }
        return snapshot

    def render_download_buttons(self, snapshot: dict):
        col1, col2 = st.columns(2)
        with col1:
            csv_data = pd.DataFrame(snapshot['events'].get('sweep_events', [])).to_csv(index=False)
            st.download_button(
                label="📊 Download Events CSV",
                data=csv_data,
                file_name=f"patterns_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
        with col2:
            json_data = json.dumps(snapshot, indent=2, default=str)
            st.download_button(
                label="📋 Download Events JSON",
                data=json_data,
                file_name=f"patterns_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )

    def create_pattern_search_interface(self):
        st.markdown("### 🔍 Deep Pattern Search")
        search_query = st.text_input(
            "Search patterns (e.g., 'sweeps > 15bps between 09:00-11:00')",
            key="pattern_search"
        )
        if search_query:
            results = self.execute_pattern_search(search_query)
            if results:
                st.dataframe(pd.DataFrame(results))
            else:
                st.info("No patterns match your search criteria")

    def execute_pattern_search(self, query: str):
        # Basic substring match placeholder
        all_events = []
        for event in self.session_state.get('sweep_events', []):
            event['event_type'] = 'sweep'
            all_events.append(event)
        return all_events

    def create_trap_predictor(self):
        from sklearn.ensemble import GradientBoostingClassifier
        self.trap_predictor = GradientBoostingClassifier(
            n_estimators=100, max_depth=3, random_state=42
        )

    def predict_next_trap(self, df: pd.DataFrame):
        # Placeholder until the model is fitted
        trap_probability = 0.42
        return {
            'trap_probability': trap_probability,
            'confidence': 0.7,
            'suggested_action': 'WAIT' if trap_probability > 0.7 else 'PROCEED',
            'key_indicators': []
        }

    def create_event_correlation_matrix(self, df: pd.DataFrame):
        event_matrix = pd.DataFrame(index=df.index)
        for event in self.session_state.get('iceberg_events', []):
            mask = (df['timestamp'] >= event['start_time']) & (df['timestamp'] <= event['end_time'])
            event_matrix.loc[mask, 'iceberg'] = 1
        event_matrix['iceberg'] = event_matrix['iceberg'].fillna(0)
        for event in self.session_state.get('spoofing_events', []):
            idx = df[df['timestamp'] == event['timestamp']].index
            if not idx.empty:
                event_matrix.loc[idx[0], 'spoofing'] = 1
        event_matrix['spoofing'] = event_matrix['spoofing'].fillna(0)
        corr_matrix = event_matrix.corr()
        fig = go.Figure(data=go.Heatmap(
            z=corr_matrix.values,
            x=corr_matrix.columns,
            y=corr_matrix.columns,
            colorscale='RdBu',
            zmid=0
        ))
        fig.update_layout(title="Event Correlation Matrix")
        st.plotly_chart(fig, use_container_width=True)

    def generate_session_narrative(self, df: pd.DataFrame, events: dict) -> str:
        narrative = []
        narrative.append(
            f"### Session Analysis: {df['timestamp'].iloc[0].strftime('%Y-%m-%d %H:%M')} - "
            f"{df['timestamp'].iloc[-1].strftime('%H:%M')}"
        )
        regime_dist = df['regime_simple'].value_counts(normalize=True) if 'regime_simple' in df else {}
        dominant_regime = regime_dist.index[0] if hasattr(regime_dist, 'index') else 'unknown'
        narrative.append(f"\n**Market Regime**: Predominantly {dominant_regime}")
        total_events = sum(len(events.get(k, [])) for k in events)
        narrative.append(f"\n**Manipulation Events**: {total_events} total events detected")
        price_change = df['price_mid'].iloc[-1] - df['price_mid'].iloc[0]
        price_change_pct = (price_change / df['price_mid'].iloc[0]) * 10000
        narrative.append(f"\n**Price Action**: {price_change_pct:+.1f} bps move")
        avg_vpin = df['vpin'].mean() if 'vpin' in df else 0
        narrative.append(f"\n**Flow Toxicity**: Average VPIN {avg_vpin:.3f}")
        return '\n'.join(narrative)

    def generate_pdf_report(self, df: pd.DataFrame, snapshot: dict, narrative: str):
        pdf_path = f"quantum_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        doc = SimpleDocTemplate(pdf_path, pagesize=letter)
        story = []
        styles = getSampleStyleSheet()
        story.append(Paragraph("Quantum Microstructure Analysis Report", styles['Title']))
        story.append(Spacer(1, 12))
        story.append(Paragraph(narrative, styles['Normal']))
        story.append(Spacer(1, 12))
        event_data = [
            ['Event Type', 'Count'],
            *[[k, len(snapshot['events'].get(k, []))] for k in snapshot['events']]
        ]
        story.append(Table(event_data))
        doc.build(story)
        return pdf_path