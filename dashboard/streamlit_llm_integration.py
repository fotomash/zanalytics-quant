import json

import plotly.graph_objects as go
import streamlit as st
import redis

from correlation_intelligence_engine import LLMNativeCorrelationEngine
from llm_redis_bridge import LLMRedisBridge


class LLMEnhancedDashboard:
    """Streamlit dashboard panel with LLM-powered correlation insights."""

    def __init__(self) -> None:
        self.redis_client = redis.Redis(host="localhost", port=6379, db=0)
        self.correlation_engine = LLMNativeCorrelationEngine(self.redis_client)
        self.llm_bridge = LLMRedisBridge(self.redis_client)

    def render_correlation_intelligence_panel(self) -> None:
        """Render panel highlighting critical correlation alerts."""
        st.header("\U0001F9E0 LLM Correlation Intelligence")
        intelligence_summary = self.llm_bridge.get_market_intelligence_summary()
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("\U0001F6A8 Critical Alerts")
            critical_alerts = intelligence_summary.get("risk_alerts", [])
            if critical_alerts:
                for alert in critical_alerts:
                    severity_color = {
                        "critical": "\U0001F534",
                        "high": "\U0001F7E0",
                        "medium": "\U0001F7E1",
                        "low": "\U0001F7E2",
                    }.get(alert.get("severity", "low"), "\u26AA")
                    st.warning(
                        f"""
{severity_color} **{alert.get('asset_pair', 'Unknown')}**  
Correlation: {alert.get('correlation', 0):.3f}  
Severity: {alert.get('severity', 'Unknown')}  
Regime Change: {'Yes' if alert.get('regime_change') else 'No'}
"""
                    )
            else:
                st.success("No critical correlation alerts")
        with col2:
            st.subheader("\U0001F4CA Live Correlation Matrix")
            correlation_data = intelligence_summary.get("correlation_analysis", {})
            if correlation_data:
                self._render_live_correlation_heatmap(correlation_data)

    def _render_live_correlation_heatmap(self, correlation_data: dict) -> None:
        assets = ["SPX", "BTC", "ETH", "DXY", "GOLD", "VIX"]
        matrix = []
        for asset1 in assets:
            row = []
            for asset2 in assets:
                if asset1 == asset2:
                    row.append(1.0)
                else:
                    pair_key = f"{asset1}_{asset2}"
                    reverse_key = f"{asset2}_{asset1}"
                    corr_value = None
                    if pair_key in correlation_data:
                        corr_value = correlation_data[pair_key].get("correlation", 0)
                    elif reverse_key in correlation_data:
                        corr_value = correlation_data[reverse_key].get("correlation", 0)
                    row.append(corr_value if corr_value is not None else 0)
            matrix.append(row)
        fig = go.Figure(
            data=go.Heatmap(
                z=matrix,
                x=assets,
                y=assets,
                colorscale="RdBu",
                zmid=0,
                text=[[f"{val:.2f}" for val in row] for row in matrix],
                texttemplate="%{text}",
                textfont={"size": 10},
                hoverongaps=False,
            )
        )
        fig.update_layout(
            title="Live Market Correlation Matrix",
            xaxis_title="Assets",
            yaxis_title="Assets",
            height=500,
        )
        st.plotly_chart(fig, use_container_width=True)

    def render_llm_insights_panel(self) -> None:
        """Display anomalies and regime changes derived from the correlation engine."""
        st.header("\U0001F916 LLM Market Insights")
        correlation_summary = self.correlation_engine.get_llm_correlation_summary()
        if correlation_summary.get("anomalies"):
            st.subheader("\u26A0\uFE0F Market Anomalies Detected")
            for anomaly in correlation_summary["anomalies"]:
                if anomaly["type"] == "dxy_vix_crisis_correlation":
                    st.error(
                        f"""
**DXY-VIX Crisis Correlation Detected**  
Current Correlation: {anomaly['value']:.3f}  
Expected: {anomaly['expected']}  
Implication: {anomaly['implication']}  
This unusual positive correlation between DXY and VIX suggests potential market stress conditions.
"""
                    )
        if correlation_summary.get("regime_changes"):
            st.subheader("\U0001F501 Regime Changes")
            for change in correlation_summary["regime_changes"]:
                st.info(
                    f"""
**{change['asset_pair']} Regime Change**  
New Correlation: {change['correlation']:.3f}  
Severity: {change['severity']}  
Time: {change['timestamp']}
"""
                )

    def render_enhanced_dashboard(self) -> None:
        """Render the full enhanced dashboard."""
        st.set_page_config(
            page_title="ZAnalytics Quant - LLM Enhanced",
            page_icon="\U0001F9E0",
            layout="wide",
        )
        st.title("\U0001F9E0 ZAnalytics Quant - LLM Enhanced Dashboard")
        self.render_correlation_intelligence_panel()
        st.divider()
        self.render_llm_insights_panel()
        if st.button("\U0001F503 Refresh Intelligence"):
            st.rerun()


if __name__ == "__main__":
    dashboard = LLMEnhancedDashboard()
    dashboard.render_enhanced_dashboard()
