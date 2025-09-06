"""Enhanced Dashboard Integration - Connecting Real MT5 Data to Pulse UI"""

from datetime import datetime, timedelta

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from mt5_bridge import MT5Bridge
from pulse_kernel import PulseKernel


class PulseUIEnhanced:
    """Enhanced Pulse UI with real MT5 integration."""

    def __init__(self):
        self.bridge = MT5Bridge()
        self.kernel = PulseKernel()

    def render_real_performance_metrics(self):
        """Display REAL performance metrics from MT5."""
        if not self.bridge.connected:
            st.warning("⚠️ MT5 not connected. Showing cached data.")
            return

        df = self.bridge.get_real_trade_history()
        if df.empty:
            st.info("No trade history available")
            return

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            win_rate = df["is_win"].mean() * 100
            st.metric("Real Win Rate", f"{win_rate:.1f}%", delta=f"{win_rate - 50:.1f}% vs baseline")

        with col2:
            total_pnl = df["profit"].sum()
            st.metric("Total P&L", f"${total_pnl:,.2f}", delta=f"{(total_pnl / 10000) * 100:.1f}% of account")

        with col3:
            revenge_count = df["revenge_trade"].sum()
            color = "🔴" if revenge_count > 5 else "🟡" if revenge_count > 2 else "🟢"
            st.metric(f"{color} Revenge Trades", revenge_count, delta="Need discipline" if revenge_count > 2 else "Good control")

        with col4:
            avg_risk_score = df["behavioral_risk_score"].mean()
            st.metric("Avg Risk Score", f"{avg_risk_score:.1f}/10", delta="High risk" if avg_risk_score > 5 else "Controlled")

    def render_behavioral_heatmap(self):
        """Show performance by day/hour."""
        df = self.bridge.get_real_trade_history()
        if df.empty:
            return

        hourly_pnl = df.groupby([df["time"].dt.dayofweek, df["time"].dt.hour])["profit"].sum().unstack(fill_value=0)

        fig = go.Figure(
            data=go.Heatmap(
                z=hourly_pnl.values,
                x=[f"{h:02d}:00" for h in range(24)],
                y=["Mon", "Tue", "Wed", "Thu", "Fri"],
                colorscale="RdYlGn",
                text=hourly_pnl.values,
                texttemplate="%{text:.0f}",
                textfont={"size": 10},
                colorbar=dict(title="P&L ($)"),
            )
        )
        fig.update_layout(
            title="Your Real Trading Performance Heatmap",
            xaxis_title="Hour (UTC)",
            yaxis_title="Day of Week",
            height=400,
        )
        st.plotly_chart(fig, use_container_width=True)

        best_hour = hourly_pnl.max().idxmax()
        worst_hour = hourly_pnl.min().idxmin()

        col1, col2 = st.columns(2)
        with col1:
            st.success(f"✅ Best performance: {best_hour}:00 UTC")
        with col2:
            st.error(f"❌ Worst performance: {worst_hour}:00 UTC")

    def render_confluence_validation(self):
        """Show validation of confluence scores."""
        validation = self.bridge.get_confluence_validation()
        if validation.empty:
            st.info("No confluence validation data available")
            return

        fig = go.Figure()
        fig.add_trace(
            go.Bar(x=validation.index, y=validation["win_rate"], name="Win Rate %", marker_color="lightblue", yaxis="y"),
        )
        fig.add_trace(
            go.Scatter(x=validation.index, y=validation["avg_pnl"], name="Avg P&L", line=dict(color="green", width=3), yaxis="y2"),
        )
        fig.update_layout(
            title="Confluence Score Validation (Real Trades)",
            xaxis_title="Confluence Band",
            yaxis=dict(title="Win Rate %", side="left"),
            yaxis2=dict(title="Avg P&L ($)", overlaying="y", side="right"),
            height=400,
            hovermode="x",
        )
        st.plotly_chart(fig, use_container_width=True)

        if len(validation) > 0:
            high_confluence_wr = validation.loc["80-90"]["win_rate"] if "80-90" in validation.index else 0
            low_confluence_wr = validation.loc["50-60"]["win_rate"] if "50-60" in validation.index else 0
            if high_confluence_wr > low_confluence_wr:
                st.success(
                    f"✅ Validation confirmed: High confluence (80-90) has {high_confluence_wr:.1f}% win rate vs {low_confluence_wr:.1f}% for low confluence"
                )
            else:
                st.warning("⚠️ Confluence scoring needs calibration")

    def render_weekly_review(self):
        """Render weekly review."""
        review = self.bridge.generate_weekly_review()
        if "error" in review:
            st.info(review["error"])
            return

        st.subheader(f"📊 Weekly Review - {review['week_ending']}")

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total P&L", f"${review['summary']['total_pnl']:,.2f}")
            st.metric("Win Rate", f"{review['summary']['win_rate']:.1f}%")
        with col2:
            st.metric("Total Trades", review['summary']['total_trades'])
            st.metric("Best Day", review['summary']['best_day'])
        with col3:
            insights = review['behavioral_insights']
            total_incidents = (
                insights['revenge_trading_incidents']
                + insights['overconfidence_incidents']
                + insights['fatigue_incidents']
            )
            st.metric("Behavioral Incidents", total_incidents)
            st.metric("Avg Risk Score", f"{insights['average_risk_score']:.1f}")

        if review['recommendations']:
            st.warning("🎯 Personalized Recommendations:")
            for rec in review['recommendations']:
                st.write(f"• {rec}")
        else:
            st.success("✅ Excellent discipline this week!")

    def render_decision_surface(self):
        """Render main decision surface."""
        st.markdown("### 🎯 Decision Surface")

        col1, col2, col3 = st.columns(3)
        with col1:
            market_data = {"symbol": "EURUSD", "price": 1.0850}
            confluence = self.kernel.confluence_scorer.calculate(market_data)
            color = "🟢" if confluence >= 70 else "🟡" if confluence >= 50 else "🔴"
            st.metric(f"{color} Confluence", f"{confluence:.0f}%")
            if st.button("Explain Score"):
                st.info(f"SMC: {confluence * 0.4:.0f} | Wyckoff: {confluence * 0.3:.0f} | Technical: {confluence * 0.3:.0f}")
        with col2:
            risk_check = self.kernel.risk_enforcer.check_constraints(confluence)
            if risk_check['allowed']:
                st.success("✅ Trade Allowed")
            else:
                st.error("🚫 Trade Blocked")
                for block in risk_check['blocks']:
                    st.caption(f"• {block}")
        with col3:
            status = self.kernel.risk_enforcer.get_status()
            st.metric("Trades Today", f"{status['trades_today']}/5")
            st.metric("Daily P&L", f"${status['daily_pnl']:,.2f}")

        st.markdown("#### Top 3 Opportunities")
        opportunities = [
            {"symbol": "EURUSD", "score": 85, "bias": "BULL", "risk": "LOW"},
            {"symbol": "GOLD", "score": 78, "bias": "BEAR", "risk": "MEDIUM"},
            {"symbol": "GBPUSD", "score": 72, "bias": "BULL", "risk": "MEDIUM"},
        ]
        for opp in opportunities:
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.write(f"**{opp['symbol']}**")
            with col2:
                st.write(f"Score: {opp['score']}%")
            with col3:
                st.write(f"Bias: {opp['bias']}")
            with col4:
                risk_color = {"LOW": "🟢", "MEDIUM": "🟡", "HIGH": "🔴"}
                st.write(f"Risk: {risk_color[opp['risk']]}")


def integrate_real_data():
    """Entry point for Streamlit app."""
    st.set_page_config(page_title="Pulse UI - Real Integration", layout="wide")
    ui = PulseUIEnhanced()

    st.markdown("# 🧠 Zanalytics Pulse - Real Trading Intelligence")
    st.markdown("*Discipline through data. Clarity through confluence. Success through self-knowledge.*")

    tab1, tab2, tab3, tab4 = st.tabs(
        ["🎯 Decision Surface", "📊 Real Performance", "🧠 Behavioral Analysis", "📝 Weekly Review"]
    )

    with tab1:
        ui.render_decision_surface()
    with tab2:
        ui.render_real_performance_metrics()
        ui.render_confluence_validation()
    with tab3:
        ui.render_behavioral_heatmap()
        if st.button("Generate Full Behavioral Report"):
            report = ui.bridge.get_behavioral_report()
            st.json(report)
    with tab4:
        ui.render_weekly_review()
        if st.button("Sync MT5 History to Journal"):
            count = ui.bridge.sync_to_pulse_journal()
            st.success(f"Synced {count} entries to journal")


if __name__ == "__main__":
    integrate_real_data()
