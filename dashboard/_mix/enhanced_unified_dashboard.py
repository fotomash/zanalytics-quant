
import sys
from pathlib import Path

# Ensure project root and ./core are on sys.path for dynamic module loading
project_root = Path(__file__).parent.resolve()
core_dir = project_root / "core"

if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
if str(core_dir) not in sys.path:
    sys.path.insert(0, str(core_dir))

"""
ZANFLOW Enhanced Unified Microstructure Dashboard
Integrating ALL discovered strategies and modules
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
import asyncio
from datetime import datetime, timedelta
import importlib
import traceback



# Enhanced Module Registry
MODULE_REGISTRY = {
    "Core Analysis": {
        "ncOS_ultimate_microstructure_analyzer": {
            "path": "ncOS_ultimate_microstructure_analyzer",
            "function": "run_comprehensive_analysis",
            "description": "Ultimate microstructure analysis with spoofing detection"
        },
        "zanflow_microstructure_analyzer": {
            "path": "zanflow_microstructure_analyzer",
            "function": "analyze_microstructure",
            "description": "Core microstructure patterns and Wyckoff analysis"
        }
    },
    "SMC Advanced": {
        "liquidity_sweep_detector": {
            "path": "core.liquidity_sweep_detector",
            "function": "detect_liquidity_sweeps",
            "description": "Detects liquidity sweeps and stop hunts"
        },
        "poi_manager_smc": {
            "path": "core.poi_manager_smc",
            "function": "find_and_validate_smc_pois",
            "description": "Manages POIs (OB, FVG, BB, MB)"
        },
        "entry_executor_smc": {
            "path": "core.entry_executor_smc",
            "function": "execute_smc_entry",
            "description": "Automated SMC entry execution"
        },
        "confirmation_engine_smc": {
            "path": "core.confirmation_engine_smc",
            "function": "confirm_smc_entry",
            "description": "Validates SMC setups"
        },
        "wick_liquidity_monitor": {
            "path": "core.wick_liquidity_monitor",
            "function": "monitor_wick_liquidity",
            "description": "Monitors wick-based liquidity patterns"
        }
    },
    "Inducement & Sweeps": {
        "liquidity_engine_smc": {
            "path": "core.liquidity_engine_smc",
            "function": "detect_inducement_from_structure",
            "description": "ZSI Agent: Inducement-Sweep-POI Framework"
        },
        "advanced_smc_orchestrator": {
            "path": "core.advanced_smc_orchestrator",
            "function": "orchestrate_smc_analysis",
            "description": "Orchestrates all SMC components"
        }
    },
    "Wyckoff Analysis": {
        "wyckoff_phase_engine": {
            "path": "core.wyckoff_phase_engine",
            "function": "detect_wyckoff_phase",
            "description": "Wyckoff phase detection"
        },
        "micro_wyckoff_phase_engine": {
            "path": "core.micro_wyckoff_phase_engine",
            "function": "detect_micro_wyckoff",
            "description": "Micro-timeframe Wyckoff analysis"
        }
    },
    "Advanced Strategies": {
        "mentfx_ici_engine": {
            "path": "core.mentfx_ici_engine",
            "function": "tag_mentfx_ici",
            "description": "MENTFX Impulse-Correction-Impulse"
        },
        "vsa_signals_mentfx": {
            "path": "core.vsa_signals_mentfx",
            "function": "detect_vsa_signals",
            "description": "Volume Spread Analysis signals"
        },
        "divergence_engine": {
            "path": "core.divergence_engine",
            "function": "detect_divergences",
            "description": "Multi-indicator divergence detection"
        },
        "fibonacci_filter": {
            "path": "core.fibonacci_filter",
            "function": "apply_fibonacci_filter",
            "description": "Advanced Fibonacci analysis"
        }
    },
    "Risk Management": {
        "risk_model": {
            "path": "core.risk_model",
            "function": "calculate_risk_metrics",
            "description": "Comprehensive risk analysis"
        },
        "advanced_stoploss_lots_engine": {
            "path": "core.advanced_stoploss_lots_engine",
            "function": "calculate_advanced_stops",
            "description": "Dynamic stop-loss calculation"
        }
    },
    "Market Intelligence": {
        "intermarket_sentiment": {
            "path": "core.intermarket_sentiment",
            "function": "analyze_intermarket",
            "description": "Cross-market correlation analysis"
        },
        "macro_sentiment_enricher": {
            "path": "core.macro_sentiment_enricher",
            "function": "enrich_macro_sentiment",
            "description": "Macro sentiment analysis"
        }
    }
}

class EnhancedLLMConnector:
    """Enhanced LLM Connector with multi-strategy integration"""

    def __init__(self):
        self.analysis_cache = {}

    async def analyze_pattern(self, pattern_data, strategy_results):
        """Comprehensive pattern analysis with all strategies"""
        prompt = f"""
        Analyze this comprehensive market situation:

        Pattern Data: {json.dumps(pattern_data, indent=2)}

        Strategy Results:
        - SMC Analysis: {strategy_results.get('smc', 'N/A')}
        - Wyckoff Phase: {strategy_results.get('wyckoff', 'N/A')}
        - Inducement/Sweep: {strategy_results.get('inducement', 'N/A')}
        - VSA Signals: {strategy_results.get('vsa', 'N/A')}
        - Risk Metrics: {strategy_results.get('risk', 'N/A')}

        Provide:
        1. Market Context (institutional perspective)
        2. Entry Strategy (specific levels and conditions)
        3. Risk Management (stops and targets)
        4. Confluence Score (0-100)
        5. Trade Recommendation
        """

        # Simulate LLM response (replace with actual API call)
        return {
            "analysis": "Multi-strategy confluence detected",
            "entry_strategy": "Wait for sweep of liquidity at X level",
            "risk_management": "Stop below structure, target at liquidity void",
            "confluence_score": 85,
            "recommendation": "HIGH PROBABILITY SETUP"
        }

    def generate_alert(self, analysis_results):
        """Generate actionable alerts from analysis"""
        alert = f"""
        🚨 ZANFLOW ALERT 🚨

        Setup: {analysis_results.get('setup_type', 'Unknown')}
        Confluence: {analysis_results.get('confluence_score', 0)}%

        Entry: {analysis_results.get('entry_level', 'TBD')}
        Stop: {analysis_results.get('stop_level', 'TBD')}
        Target: {analysis_results.get('target_level', 'TBD')}

        Bias: {analysis_results.get('bias', 'Neutral')}
        """
        return alert

class UnifiedAnalysisEngine:
    """Orchestrates all analysis modules"""

    def __init__(self):
        self.loaded_modules = {}
        self.llm_connector = EnhancedLLMConnector()

    def load_module(self, module_path, function_name):
        """Dynamically load analysis modules"""
        try:
            if module_path not in self.loaded_modules:
                module = importlib.import_module(module_path)
                self.loaded_modules[module_path] = module

            return getattr(self.loaded_modules[module_path], function_name, None)
        except Exception as e:
            st.error(f"Failed to load {module_path}: {str(e)}")
            return None

    async def run_comprehensive_analysis(self, df, selected_strategies):
        """Run all selected analysis strategies"""
        results = {}

        with st.spinner("Running comprehensive analysis..."):
            progress_bar = st.progress(0)
            total_strategies = len(selected_strategies)

            for idx, (category, strategies) in enumerate(selected_strategies.items()):
                for strategy_name, strategy_info in strategies.items():
                    try:
                        # Load and execute strategy
                        func = self.load_module(
                            strategy_info['path'], 
                            strategy_info['function']
                        )

                        if func:
                            st.info(f"Running {strategy_name}...")
                            result = func(df)
                            results[strategy_name] = result

                    except Exception as e:
                        st.warning(f"{strategy_name} error: {str(e)}")
                        results[strategy_name] = {"error": str(e)}

                progress_bar.progress((idx + 1) / len(selected_strategies))

            # LLM Analysis
            if results:
                llm_analysis = await self.llm_connector.analyze_pattern(
                    {"timestamp": datetime.now().isoformat()},
                    results
                )
                results['llm_analysis'] = llm_analysis

        return results

# Main Dashboard
def main():
    st.title("🚀 ZANFLOW Enhanced Unified Dashboard")
    st.markdown("*Integrating ALL discovered strategies and modules*")

    # Sidebar
    with st.sidebar:
        st.header("⚙️ Configuration")

        # Module Selection
        st.subheader("📊 Select Analysis Modules")
        selected_modules = {}

        for category, modules in MODULE_REGISTRY.items():
            st.markdown(f"**{category}**")
            selected_modules[category] = {}

            for module_name, module_info in modules.items():
                if st.checkbox(
                    module_name.replace('_', ' ').title(),
                    value=True,
                    help=module_info['description']
                ):
                    selected_modules[category][module_name] = module_info

        # Data Source
        st.subheader("📁 Data Source")
        data_source = st.selectbox(
            "Select Data",
            ["Upload CSV", "Enriched_Tick_Data.csv", "XAUUSD_tick.csv"]
        )

        if data_source == "Upload CSV":
            uploaded_file = st.file_uploader("Upload tick data", type=['csv'])

        # Analysis Settings
        st.subheader("🎯 Analysis Settings")
        lookback_period = st.slider("Lookback Period", 100, 5000, 1000)

        # LLM Settings
        st.subheader("🤖 LLM Configuration")
        use_llm = st.checkbox("Enable LLM Analysis", value=True)
        llm_model = st.selectbox(
            "LLM Model",
            ["Claude Opus", "GPT-4", "Custom Model"]
        )

    # Main Content
    col1, col2 = st.columns([3, 1])

    with col1:
        # Load Data
        import os

        # Use Streamlit secrets for directories, with fallback to current directory
        enriched_dir = st.secrets.get("enriched_data", ".")
        tick_dir = st.secrets.get("tick_data", ".")

        df = None
        if data_source == "Enriched_Tick_Data.csv":
            enriched_path = os.path.join(enriched_dir, "Enriched_Tick_Data.csv")
            if os.path.exists(enriched_path):
                df = pd.read_csv(enriched_path)
            else:
                st.warning(f"File not found: {enriched_path}. Please upload manually below.")
                uploaded_file = st.file_uploader("Upload Enriched Tick Data CSV", type=['csv'])
                if uploaded_file:
                    df = pd.read_csv(uploaded_file)
        elif data_source == "XAUUSD_tick.csv":
            tick_path = os.path.join(tick_dir, "XAUUSD_tick.csv")
            if os.path.exists(tick_path):
                df = pd.read_csv(tick_path)
            else:
                st.warning(f"File not found: {tick_path}. Please upload manually below.")
                uploaded_file = st.file_uploader("Upload XAUUSD Tick Data CSV", type=['csv'])
                if uploaded_file:
                    df = pd.read_csv(uploaded_file)
        elif uploaded_file:
            df = pd.read_csv(uploaded_file)

        if df is not None:
            # Data Preview
            st.subheader("📈 Data Overview")
            st.dataframe(df.head(), use_container_width=True)

            # Run Analysis
            if st.button("🚀 Run Comprehensive Analysis", type="primary"):
                engine = UnifiedAnalysisEngine()

                # Run async analysis
                results = asyncio.run(
                    engine.run_comprehensive_analysis(df, selected_modules)
                )

                # Display Results
                st.subheader("📊 Analysis Results")

                # Create tabs for different result categories
                tabs = st.tabs([
                    "Summary", "SMC Analysis", "Wyckoff", 
                    "Risk Analysis", "LLM Insights", "Raw Data"
                ])

                with tabs[0]:  # Summary
                    if 'llm_analysis' in results:
                        llm = results['llm_analysis']

                        # Metrics
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            st.metric(
                                "Confluence Score",
                                f"{llm.get('confluence_score', 0)}%"
                            )
                        with col2:
                            st.metric(
                                "Setup Quality",
                                llm.get('recommendation', 'N/A')
                            )
                        with col3:
                            st.metric(
                                "Risk:Reward",
                                "1:3"  # Calculate from results
                            )
                        with col4:
                            st.metric(
                                "Strategies Aligned",
                                f"{len([r for r in results.values() if not isinstance(r, dict) or 'error' not in r])}"
                            )

                        # Alert
                        alert = engine.llm_connector.generate_alert(llm)
                        st.info(alert)

                with tabs[1]:  # SMC Analysis
                    smc_results = {k: v for k, v in results.items() if 'smc' in k.lower()}
                    for name, result in smc_results.items():
                        st.markdown(f"**{name}**")
                        st.json(result)

                with tabs[2]:  # Wyckoff
                    wyckoff_results = {k: v for k, v in results.items() if 'wyckoff' in k.lower()}
                    for name, result in wyckoff_results.items():
                        st.markdown(f"**{name}**")
                        st.json(result)

                with tabs[3]:  # Risk Analysis
                    risk_results = {k: v for k, v in results.items() if 'risk' in k.lower()}
                    for name, result in risk_results.items():
                        st.markdown(f"**{name}**")
                        st.json(result)

                with tabs[4]:  # LLM Insights
                    if 'llm_analysis' in results:
                        st.markdown("### 🤖 AI-Powered Market Insights")
                        llm = results['llm_analysis']
                        st.markdown(f"**Analysis:** {llm.get('analysis')}")
                        st.markdown(f"**Entry Strategy:** {llm.get('entry_strategy')}")
                        st.markdown(f"**Risk Management:** {llm.get('risk_management')}")

                with tabs[5]:  # Raw Data
                    st.json(results)

    with col2:
        # Quick Stats
        st.subheader("📊 Quick Stats")
        if df is not None:
            st.metric("Total Ticks", len(df))
            st.metric("Time Range", f"{df.iloc[0]['timestamp']} to {df.iloc[-1]['timestamp']}")

            # Module Status
            st.subheader("🔌 Module Status")
            total_modules = sum(len(modules) for modules in MODULE_REGISTRY.values())
            selected_count = sum(
                len(mods) for cat_mods in selected_modules.values() 
                for mods in cat_mods.values()
            )
            st.metric("Active Modules", f"{selected_count}/{total_modules}")

            # Strategy Distribution
            st.subheader("📈 Strategy Mix")
            strategy_counts = {}
            for category in selected_modules:
                count = len(selected_modules[category])
                if count > 0:
                    strategy_counts[category] = count

            if strategy_counts:
                fig = go.Figure(data=[
                    go.Pie(
                        labels=list(strategy_counts.keys()),
                        values=list(strategy_counts.values()),
                        hole=0.3
                    )
                ])
                fig.update_layout(height=300, showlegend=False)
                st.plotly_chart(fig, use_container_width=True)

if __name__ == "__main__":
    main()
