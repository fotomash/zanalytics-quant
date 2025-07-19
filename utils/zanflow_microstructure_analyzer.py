#!/usr/bin/env python3
"""
XAUUSD Microstructure & Advanced Strategy Analysis Dashboard
Created for ZANFLOW v12 Trading System

This script analyzes tick data for:
1. Microstructure patterns and manipulation detection
2. Wyckoff analysis
3. Smart Money Concepts (SMC)
4. Inducement patterns
5. Rich market commentary

Author: AI Assistant for ZANFLOW v12
Date: 2025-06-25

Moved to core/zanflow_microstructure_analyzer.py for import as:
    from core.zanflow_microstructure_analyzer import MicrostructureAnalyzer
"""

import argparse
import json
import os
import re
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
import seaborn as sns
from matplotlib.gridspec import GridSpec
import matplotlib.ticker as mticker
import warnings
warnings.filterwarnings('ignore')

class MicrostructureAnalyzer:
    def __init__(self, tick_file_path, limit_ticks=None, export_json=False, no_dashboard=False, output_dir="."):
        """Initialize the analyzer with tick data"""
        self.tick_file_path = tick_file_path
        self.tick_df = None
        self.analysis_results = {}
        self.limit_ticks = limit_ticks
        self.export_json = export_json
        self.no_dashboard = no_dashboard
        self.output_dir = output_dir

    def load_data(self):
        """Load and preprocess tick data"""
        print("Loading tick data...")
        try:
            # Use pandas' automatic delimiter detection
            self.tick_df = pd.read_csv(self.tick_file_path, sep=None, engine='python')

            # Validate required columns
            required_cols = {"timestamp", "bid", "ask"}
            if not required_cols.issubset(self.tick_df.columns):
                # Try fallbacks
                for _sep in ["\t", ","]:
                    self.tick_df = pd.read_csv(self.tick_file_path, sep=_sep)
                    if required_cols.issubset(self.tick_df.columns):
                        break
                else:
                    missing = ", ".join(required_cols - set(self.tick_df.columns))
                    raise ValueError(
                        f"Missing required columns ({missing}) in '{self.tick_file_path}'. "
                        "Check the delimiter or header names."
                    )

            # Convert timestamp to datetime
            self.tick_df['datetime'] = pd.to_datetime(self.tick_df['timestamp'])
            # Ensure spread_price exists; if absent, derive it from ask‑bid
            if 'spread_price' not in self.tick_df.columns:
                self.tick_df['spread_price'] = self.tick_df['ask'] - self.tick_df['bid']

            # Calculate derived metrics
            self.tick_df['mid_price'] = (self.tick_df['bid'] + self.tick_df['ask']) / 2
            self.tick_df['price_change'] = self.tick_df['mid_price'].diff()
            self.tick_df['spread_pips'] = self.tick_df['spread_price'] * 100
            self.tick_df['volatility'] = self.tick_df['price_change'].abs()
            self.tick_df['ba_imbalance'] = (self.tick_df['ask'] - self.tick_df['bid']) / (self.tick_df['ask'] + self.tick_df['bid'])

            if self.limit_ticks:
                self.tick_df = self.tick_df.tail(self.limit_ticks)

            print(f"Successfully loaded {len(self.tick_df)} ticks")
            return True

        except Exception as e:
            print(f"Error loading data: {e}")
            return False

    def detect_manipulation_patterns(self):
        """Detect various manipulation patterns in the tick data"""
        print("Detecting manipulation patterns...")

        # 1. Sudden spread widening
        spread_threshold = self.tick_df['spread_pips'].mean() + 2 * self.tick_df['spread_pips'].std()
        self.tick_df['spread_spike'] = self.tick_df['spread_pips'] > spread_threshold

        # 2. Price reversal after spread spike
        self.tick_df['price_reversal'] = False
        for i in range(3, len(self.tick_df)):
            if self.tick_df.iloc[i-3:i-1]['spread_spike'].any() and abs(self.tick_df.iloc[i]['price_change']) > 0.05:
                self.tick_df.loc[self.tick_df.index[i], 'price_reversal'] = True

        # 3. Stop hunts (sharp price movement followed by reversal)
        window_size = 10
        self.tick_df['stop_hunt'] = False
        for i in range(window_size, len(self.tick_df)):
            price_move = self.tick_df.iloc[i-window_size:i]['price_change'].sum()
            next_move = self.tick_df.iloc[i:i+5]['price_change'].sum() if i+5 < len(self.tick_df) else 0
            if abs(price_move) > 0.1 and price_move * next_move < 0:
                self.tick_df.loc[self.tick_df.index[i], 'stop_hunt'] = True

        # 4. Liquidity sweeps
        self.tick_df['liquidity_sweep'] = False
        for i in range(20, len(self.tick_df)):
            if i+10 < len(self.tick_df):
                pre_high = self.tick_df.iloc[i-20:i]['mid_price'].max()
                pre_low = self.tick_df.iloc[i-20:i]['mid_price'].min()
                curr_price = self.tick_df.iloc[i]['mid_price']
                next_price = self.tick_df.iloc[i+10]['mid_price']

                # High sweep or Low sweep
                if (curr_price > pre_high and next_price < pre_high) or \
                   (curr_price < pre_low and next_price > pre_low):
                    self.tick_df.loc[self.tick_df.index[i], 'liquidity_sweep'] = True

        # Store results
        self.analysis_results['spread_spikes'] = len(self.tick_df[self.tick_df['spread_spike']])
        self.analysis_results['price_reversals'] = len(self.tick_df[self.tick_df['price_reversal']])
        self.analysis_results['stop_hunts'] = len(self.tick_df[self.tick_df['stop_hunt']])
        self.analysis_results['liquidity_sweeps'] = len(self.tick_df[self.tick_df['liquidity_sweep']])

    def wyckoff_analysis(self):
        """Perform Wyckoff phase analysis"""
        print("Performing Wyckoff analysis...")

        self.tick_df['wyckoff_phase'] = np.nan
        window = 100

        if len(self.tick_df) > window:
            for i in range(window, len(self.tick_df), window//2):
                if i+window < len(self.tick_df):
                    segment = self.tick_df.iloc[i-window:i+window]

                    # Accumulation
                    if (segment['mid_price'].iloc[:window//2].mean() < segment['mid_price'].iloc[window//2:].mean() and
                        segment['volatility'].iloc[:window//2].mean() > segment['volatility'].iloc[window//2:].mean()):
                        self.tick_df.loc[self.tick_df.index[i-window//2:i+window//2], 'wyckoff_phase'] = 1

                    # Distribution
                    elif (segment['mid_price'].iloc[:window//2].mean() > segment['mid_price'].iloc[window//2:].mean() and
                          segment['volatility'].iloc[:window//2].mean() < segment['volatility'].iloc[window//2:].mean()):
                        self.tick_df.loc[self.tick_df.index[i-window//2:i+window//2], 'wyckoff_phase'] = 2

                    # Markup
                    elif (segment['mid_price'].diff().iloc[:window].mean() > 0 and
                          segment['mid_price'].diff().iloc[window:].mean() > 0):
                        self.tick_df.loc[self.tick_df.index[i-window//2:i+window//2], 'wyckoff_phase'] = 3

                    # Markdown
                    elif (segment['mid_price'].diff().iloc[:window].mean() < 0 and
                          segment['mid_price'].diff().iloc[window:].mean() < 0):
                        self.tick_df.loc[self.tick_df.index[i-window//2:i+window//2], 'wyckoff_phase'] = 4

        # Store results
        self.analysis_results['wyckoff_phases'] = {1: 0, 2: 0, 3: 0, 4: 0}
        for phase in [1, 2, 3, 4]:
            count = len(self.tick_df[self.tick_df['wyckoff_phase'] == phase])
            self.analysis_results['wyckoff_phases'][phase] = count

    def smc_analysis(self):
        """Perform Smart Money Concepts analysis"""
        print("Performing SMC analysis...")

        # Resample to 1‑minute bars (first tick of each minute)
        minute_data = (
            self.tick_df
            .set_index('datetime')
            .resample('1Min')
            .first()
            .dropna(subset=['mid_price'])
            .reset_index()
        )

        minute_data['fvg_up'] = False
        minute_data['fvg_down'] = False

        # Detect Fair Value Gaps
        if len(minute_data) > 3:
            for i in range(2, len(minute_data)):
                if minute_data['mid_price'].iloc[i-2] > minute_data['mid_price'].iloc[i]:
                    minute_data.iloc[i-1, minute_data.columns.get_loc('fvg_up')] = True

                if minute_data['mid_price'].iloc[i-2] < minute_data['mid_price'].iloc[i]:
                    minute_data.iloc[i-1, minute_data.columns.get_loc('fvg_down')] = True

        self.minute_data = minute_data
        self.analysis_results['bullish_fvgs'] = len(minute_data[minute_data['fvg_up'] == True])
        self.analysis_results['bearish_fvgs'] = len(minute_data[minute_data['fvg_down'] == True])

    def inducement_analysis(self):
        """Detect inducement patterns"""
        print("Performing inducement analysis...")

        self.tick_df['inducement'] = False
        self.tick_df['inducement_level'] = np.nan
        self.tick_df['inducement_type'] = ''

        window = 50
        if len(self.tick_df) > window:
            for i in range(window, len(self.tick_df)-window):
                pre_segment = self.tick_df.iloc[i-window:i]
                post_segment = self.tick_df.iloc[i:i+window]

                pre_high = pre_segment['mid_price'].max()
                pre_low = pre_segment['mid_price'].min()

                # High inducement
                if (self.tick_df.iloc[i]['mid_price'] > pre_high and 
                    post_segment['mid_price'].iloc[10:].mean() < self.tick_df.iloc[i]['mid_price']):
                    self.tick_df.loc[self.tick_df.index[i], 'inducement'] = True
                    self.tick_df.loc[self.tick_df.index[i], 'inducement_level'] = pre_high
                    self.tick_df.loc[self.tick_df.index[i], 'inducement_type'] = 'High'

                # Low inducement
                if (self.tick_df.iloc[i]['mid_price'] < pre_low and 
                    post_segment['mid_price'].iloc[10:].mean() > self.tick_df.iloc[i]['mid_price']):
                    self.tick_df.loc[self.tick_df.index[i], 'inducement'] = True
                    self.tick_df.loc[self.tick_df.index[i], 'inducement_level'] = pre_low
                    self.tick_df.loc[self.tick_df.index[i], 'inducement_type'] = 'Low'

        inducements = self.tick_df[self.tick_df['inducement']]
        self.analysis_results['high_inducements'] = len(inducements[inducements['inducement_type'] == 'High'])
        self.analysis_results['low_inducements'] = len(inducements[inducements['inducement_type'] == 'Low'])

    def create_dashboard(self):
        """Create the comprehensive analysis dashboard"""
        print("Creating dashboard...")

        import os
        # Extract trading pair name from file path (normalized)
        raw_name = os.path.splitext(os.path.basename(self.tick_file_path))[0]
        pair_name = re.sub(r'[_\-]?ticks?$', '', raw_name, flags=re.IGNORECASE).upper()

        plt.style.use('dark_background')
        fig = plt.figure(figsize=(20, 24))
        gs = GridSpec(6, 2, figure=fig)

        # 1. Main price chart with manipulation markers
        ax1 = fig.add_subplot(gs[0, :])
        ax1.plot(self.tick_df['datetime'], self.tick_df['mid_price'], color='white', linewidth=1, label='Mid Price')

        # Mark manipulation patterns
        spread_spikes = self.tick_df[self.tick_df['spread_spike']]
        price_reversals = self.tick_df[self.tick_df['price_reversal']]
        stop_hunts = self.tick_df[self.tick_df['stop_hunt']]
        liquidity_sweeps = self.tick_df[self.tick_df['liquidity_sweep']]

        if not spread_spikes.empty:
            ax1.scatter(spread_spikes['datetime'], spread_spikes['mid_price'],
                       color='yellow', s=50, marker='^', label='Spread Spike')
        if not price_reversals.empty:
            ax1.scatter(price_reversals['datetime'], price_reversals['mid_price'],
                       color='red', s=50, marker='x', label='Price Reversal')
        if not stop_hunts.empty:
            ax1.scatter(stop_hunts['datetime'], stop_hunts['mid_price'],
                       color='magenta', s=50, marker='o', label='Stop Hunt')
        if not liquidity_sweeps.empty:
            ax1.scatter(liquidity_sweeps['datetime'], liquidity_sweeps['mid_price'],
                       color='cyan', s=50, marker='s', label='Liquidity Sweep')

        ax1.set_title(f'{pair_name} Price with Microstructure Manipulation Markers', fontsize=16)
        ax1.set_ylabel('Price', fontsize=12)
        ax1.legend(loc='upper left')
        ax1.grid(True, alpha=0.3)

        # 2. Spread analysis
        ax2 = fig.add_subplot(gs[1, 0])
        ax2.plot(self.tick_df['datetime'], self.tick_df['spread_pips'], color='orange', linewidth=1)
        ax2.set_title('Spread Analysis (Pips)', fontsize=16)
        ax2.set_ylabel('Spread (Pips)', fontsize=12)
        ax2.grid(True, alpha=0.3)

        # 3. Volatility
        ax3 = fig.add_subplot(gs[1, 1])
        ax3.plot(self.tick_df['datetime'], self.tick_df['volatility'].rolling(20).mean(), color='red', linewidth=1)
        ax3.set_title('Tick Volatility (20-tick Rolling Average)', fontsize=16)
        ax3.set_ylabel('Volatility', fontsize=12)
        ax3.grid(True, alpha=0.3)

        # 4. Bid-Ask imbalance
        ax4 = fig.add_subplot(gs[2, 0])
        ax4.plot(self.tick_df['datetime'], self.tick_df['ba_imbalance'].rolling(20).mean() * 10000,
                color='purple', linewidth=1)
        ax4.set_title('Bid-Ask Imbalance (×10,000)', fontsize=16)
        ax4.set_ylabel('Imbalance', fontsize=12)
        ax4.grid(True, alpha=0.3)

        # 5. Price change distribution
        ax5 = fig.add_subplot(gs[2, 1])
        sns.histplot(self.tick_df['price_change'].dropna(), bins=50, kde=True, color='cyan', ax=ax5)
        ax5.set_title('Price Change Distribution (Microstructure)', fontsize=16)
        ax5.set_xlabel('Tick-to-Tick Price Change', fontsize=12)
        ax5.grid(True, alpha=0.3)

        # 6. Manipulation events timeline
        ax6 = fig.add_subplot(gs[3, :])
        events = []
        labels = []
        colors = []

        for idx, row in spread_spikes.iterrows():
            events.append((row['datetime'], 'Spread Spike', 'yellow'))
        for idx, row in price_reversals.iterrows():
            events.append((row['datetime'], 'Price Reversal', 'red'))
        for idx, row in stop_hunts.iterrows():
            events.append((row['datetime'], 'Stop Hunt', 'magenta'))
        for idx, row in liquidity_sweeps.iterrows():
            events.append((row['datetime'], 'Liquidity Sweep', 'cyan'))

        events.sort(key=lambda x: x[0])

        for i, (dt, event, color) in enumerate(events):
            ax6.scatter(dt, 0, color=color, s=100, marker='|')
            if i % 10 == 0:
                ax6.text(dt, 0.1, event, rotation=45, fontsize=8, color=color)

        ax6.set_title('Manipulation Events Timeline', fontsize=16)
        ax6.set_yticks([])
        ax6.grid(True, alpha=0.3)

        # 7. Wyckoff phases
        ax7 = fig.add_subplot(gs[4, 0])
        ax7.plot(self.tick_df['datetime'], self.tick_df['mid_price'], color='white', linewidth=1, alpha=0.5)

        colors = {1: 'blue', 2: 'red', 3: 'green', 4: 'orange'}
        labels = {1: 'Accumulation', 2: 'Distribution', 3: 'Markup', 4: 'Markdown'}

        for phase in [1, 2, 3, 4]:
            phase_data = self.tick_df[self.tick_df['wyckoff_phase'] == phase]
            if not phase_data.empty:
                ax7.scatter(phase_data['datetime'], phase_data['mid_price'],
                           color=colors[phase], label=labels[phase], alpha=0.7, s=10)

        ax7.set_title('Wyckoff Phase Analysis', fontsize=16)
        ax7.set_ylabel('Price', fontsize=12)
        ax7.legend(loc='upper left')
        ax7.grid(True, alpha=0.3)

        # 8. SMC analysis
        ax8 = fig.add_subplot(gs[4, 1])
        ax8.plot(self.minute_data['datetime'], self.minute_data['mid_price'], color='white', linewidth=1, alpha=0.7)

        fvg_up = self.minute_data[self.minute_data['fvg_up'] == True]
        fvg_down = self.minute_data[self.minute_data['fvg_down'] == True]

        if not fvg_up.empty:
            ax8.scatter(fvg_up['datetime'], fvg_up['mid_price'], color='green', s=50, marker='^', label='Bullish FVG')
        if not fvg_down.empty:
            ax8.scatter(fvg_down['datetime'], fvg_down['mid_price'], color='red', s=50, marker='v', label='Bearish FVG')

        ax8.set_title('Smart Money Concepts - Fair Value Gaps', fontsize=16)
        ax8.set_ylabel('Price', fontsize=12)
        ax8.legend(loc='upper left')
        ax8.grid(True, alpha=0.3)

        # 9. Inducement analysis
        ax9 = fig.add_subplot(gs[5, :])
        ax9.plot(self.tick_df['datetime'], self.tick_df['mid_price'], color='white', linewidth=1)

        inducements = self.tick_df[self.tick_df['inducement']]
        high_inducements = inducements[inducements['inducement_type'] == 'High']
        low_inducements = inducements[inducements['inducement_type'] == 'Low']

        if not high_inducements.empty:
            ax9.scatter(high_inducements['datetime'], high_inducements['mid_price'],
                       color='red', s=80, marker='v', label='High Inducement')
        if not low_inducements.empty:
            ax9.scatter(low_inducements['datetime'], low_inducements['mid_price'],
                       color='green', s=80, marker='^', label='Low Inducement')

        for idx, row in inducements.iterrows():
            ax9.axhline(y=row['inducement_level'], color='yellow', linestyle='--', alpha=0.3)

        ax9.set_title('Inducement Analysis - Institutional Order Flow', fontsize=16)
        ax9.set_ylabel('Price', fontsize=12)
        ax9.legend(loc='upper left')
        ax9.grid(True, alpha=0.3)

        # Format x-axis dates
        for ax in [ax1, ax2, ax3, ax4, ax6, ax7, ax8, ax9]:
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)

        plt.tight_layout()
        plt.suptitle(f'{pair_name} Tick Data Microstructure Analysis Dashboard', fontsize=24, y=1.02)
        from datetime import datetime
        tick_count = len(self.tick_df)
        filename = f"{pair_name}_{tick_count}tick.png"
        output_folder = os.path.join(self.output_dir, pair_name)
        os.makedirs(output_folder, exist_ok=True)
        dashboard_path = os.path.join(output_folder, filename)
        plt.savefig(dashboard_path, dpi=300, bbox_inches='tight')
        print(f"📊 Dashboard saved at: {dashboard_path}")
        # Store filename for use in main
        self.dashboard_filename = filename

    def generate_report(self):
        """Generate comprehensive analysis report (single block boxed format)"""
        import os
        from datetime import datetime
        raw_name = os.path.splitext(os.path.basename(self.tick_file_path))[0]
        pair_name = re.sub(r'[_\-]?ticks?$', '', raw_name, flags=re.IGNORECASE).upper()

        # Metrics
        analysis_period = f"{self.tick_df['datetime'].min()} to {self.tick_df['datetime'].max()}"
        total_ticks = len(self.tick_df)
        price_min = self.tick_df['mid_price'].min()
        price_max = self.tick_df['mid_price'].max()
        price_range = f"{price_min:.2f} - {price_max:.2f}"
        overall_trend = "BULLISH" if self.tick_df['mid_price'].iloc[-1] > self.tick_df['mid_price'].iloc[0] else "BEARISH"
        price_change = self.tick_df['mid_price'].iloc[-1] - self.tick_df['mid_price'].iloc[0]

        avg_spread = self.tick_df['spread_pips'].mean()
        max_spread = self.tick_df['spread_pips'].max()
        spread_vol = self.tick_df['spread_pips'].std()
        avg_volatility = self.tick_df['volatility'].mean()

        # Manipulation
        spread_spikes = self.analysis_results['spread_spikes']
        price_reversals = self.analysis_results['price_reversals']
        stop_hunts = self.analysis_results['stop_hunts']
        liquidity_sweeps = self.analysis_results['liquidity_sweeps']
        manipulation_score = (spread_spikes + stop_hunts + liquidity_sweeps) / total_ticks * 100
        if manipulation_score > 5:
            manipulation_label = "🔴 HIGH MANIPULATION ACTIVITY - Institutional traders very active"
        elif manipulation_score > 2:
            manipulation_label = "🟡 MODERATE MANIPULATION ACTIVITY - Some institutional involvement"
        else:
            manipulation_label = "🟢 LOW MANIPULATION ACTIVITY - Relatively clean price action"

        # Wyckoff
        wyckoff_counts = self.analysis_results['wyckoff_phases']
        wyckoff_lines = []
        for phase, count in wyckoff_counts.items():
            pct = (count / total_ticks) * 100
            phase_name = {1: "Accumulation", 2: "Distribution", 3: "Markup", 4: "Markdown"}.get(phase, str(phase))
            wyckoff_lines.append(f"{phase_name}: {count:,} ticks ({pct:.1f}%)")
        dominant_phase_num = max(wyckoff_counts, key=wyckoff_counts.get)
        dominant_phase = {1: "Accumulation", 2: "Distribution", 3: "Markup", 4: "Markdown"}.get(dominant_phase_num, str(dominant_phase_num))

        # SMC
        bullish_fvgs = self.analysis_results['bullish_fvgs']
        bearish_fvgs = self.analysis_results['bearish_fvgs']
        fvg_bias = "BULLISH" if bullish_fvgs > bearish_fvgs else "BEARISH"

        # Inducement
        high_inducements = self.analysis_results['high_inducements']
        low_inducements = self.analysis_results['low_inducements']
        total_inducements = high_inducements + low_inducements
        inducement_rate = (total_inducements / total_ticks) * 100

        # Commentary
        commentary = []
        if manipulation_score > 5:
            commentary.append("🚨 HEAVY institutional manipulation detected. Price action is being heavily engineered.")
        if stop_hunts > total_ticks * 0.1:
            commentary.append("🎯 Frequent stop hunting indicates aggressive institutional order flow.")
        if liquidity_sweeps > 100:
            commentary.append("💧 Multiple liquidity sweeps show smart money collecting orders at key levels.")
        if dominant_phase == "Accumulation":
            commentary.append("📈 Accumulation phase suggests preparation for potential markup.")
        elif dominant_phase == "Distribution":
            commentary.append("📉 Distribution phase indicates potential bearish reversal ahead.")
        if fvg_bias == "BULLISH" and overall_trend == "BEARISH":
            commentary.append("⚔️ SMC shows bullish bias while trend is bearish - potential reversal setup.")
        if inducement_rate > 5:
            commentary.append("🪤 High inducement activity - many retail traders being trapped.")

        # Recommendations
        recommendations = []
        if fvg_bias == "BULLISH":
            recommendations.append("✅ Focus on LONG setups at Fair Value Gap levels")
        else:
            recommendations.append("✅ Focus on SHORT setups at Fair Value Gap levels")
        if dominant_phase == "Accumulation":
            recommendations.append("✅ Prepare for potential MARKUP phase - look for breakout setups")
        elif dominant_phase == "Distribution":
            recommendations.append("✅ Be cautious of reversals - consider SHORT bias")
        if manipulation_score > 5:
            recommendations.append("⚠️ Use wider stops due to high manipulation activity")
            recommendations.append("⚠️ Consider smaller position sizes in this volatile environment")
        if high_inducements > low_inducements:
            recommendations.append("📍 Watch for shorts around recent highs (inducement levels)")
        else:
            recommendations.append("📍 Watch for longs around recent lows (inducement levels)")
        recommendations.append("🔄 Monitor price reaction at identified Fair Value Gap levels")
        recommendations.append("🎯 Use liquidity sweep levels as potential reversal zones")

        # Strategy insights
        total_fvgs = bullish_fvgs + bearish_fvgs
        phase_dist = "trending" if max(wyckoff_counts.values()) > total_ticks * 0.4 else "ranging"
        market_complexity = "HIGH" if manipulation_score > 5 else "MODERATE" if manipulation_score > 2 else "LOW"

        summary_block = f"""
{'='*80}
{pair_name} MICROSTRUCTURE & ADVANCED STRATEGY ANALYSIS REPORT
{'='*80}

Analysis Period: {analysis_period}
Total Ticks Analyzed: {total_ticks:,}
Price Range: {price_range}
Overall Trend: {overall_trend} ({price_change:+.2f} points)

{'-'*50}
MICROSTRUCTURE ANALYSIS
{'-'*50}
Average Spread: {avg_spread:.2f} pips
Maximum Spread: {max_spread:.2f} pips
Spread Volatility: {spread_vol:.2f} pips
Average Tick Volatility: {avg_volatility:.4f}

{'-'*50}
MANIPULATION DETECTION
{'-'*50}
Spread Spikes: {spread_spikes} detected
Price Reversals: {price_reversals} detected
Stop Hunts: {stop_hunts} detected
Liquidity Sweeps: {liquidity_sweeps} detected

Manipulation Activity Score: {manipulation_score:.2f}%
{manipulation_label}

{'-'*50}
WYCKOFF ANALYSIS
{'-'*50}
""" + "\n".join(wyckoff_lines) + f"""

Dominant Phase: {dominant_phase}

{'-'*50}
SMART MONEY CONCEPTS (SMC)
{'-'*50}
Bullish Fair Value Gaps: {bullish_fvgs}
Bearish Fair Value Gaps: {bearish_fvgs}
SMC Bias: {fvg_bias}

{'-'*50}
INDUCEMENT ANALYSIS
{'-'*50}
High Inducements (Trapping Longs): {high_inducements}
Low Inducements (Trapping Shorts): {low_inducements}
Inducement Rate: {inducement_rate:.2f}%

{'-'*50}
EXPERT COMMENTARY
{'-'*50}
""" + ("\n".join(commentary) if commentary else "No major commentary.") + f"""

{'-'*50}
TRADING STRATEGY RECOMMENDATIONS
{'-'*50}
""" + "\n".join(recommendations) + f"""

{'-'*50}
V5, V10, V12 STRATEGY INSIGHTS
{'-'*50}
V5 Strategy (Basic SMC):
  - {total_fvgs} FVG opportunities identified
  - Bias: {fvg_bias}

V10 Strategy (Advanced Wyckoff):
  - Current market phase: {dominant_phase}
  - Phase distribution suggests {phase_dist} market

V12 Strategy (Full ZANFLOW):
  - Manipulation score: {manipulation_score:.2f}%
  - Inducement activity: {inducement_rate:.2f}%
  - Market complexity: {market_complexity}

{'='*80}
END OF ANALYSIS REPORT
{'='*80}
"""

        print(summary_block)

        # Save report to file in symbol-named subdirectory with simplified filename
        report_folder = os.path.join(self.output_dir, pair_name)
        os.makedirs(report_folder, exist_ok=True)
        report_filename = f"{pair_name}_{total_ticks}tick.txt"
        report_path = os.path.join(report_folder, report_filename)
        with open(report_path, "w") as report_file:
            report_file.write(summary_block)
        print(f"📄 Text report saved at: {report_path}")

    def run_full_analysis(self):
        """Run the complete analysis pipeline"""
        if not self.load_data():
            return False

        self.detect_manipulation_patterns()
        self.wyckoff_analysis()
        self.smc_analysis()
        self.inducement_analysis()
        if not self.no_dashboard:
            self.create_dashboard()
        self.generate_report()

        # After all processing, update self.dashboard_filename to include full relative path (subfolder)
        import os
        import re
        raw_name = os.path.splitext(os.path.basename(self.tick_file_path))[0]
        pair_name = re.sub(r'[_\-]?ticks?$', '', raw_name, flags=re.IGNORECASE).upper()
        total_ticks = len(self.tick_df)
        self.dashboard_filename = os.path.join(pair_name, f"{pair_name}_{total_ticks}tick.png")

        if self.export_json:
            from datetime import datetime  # already imported earlier, but safe to re‑import in local scope
            # Use same pair_name, total_ticks as above
            json_filename = f"{pair_name}_{total_ticks}tick.json"
            output_folder = os.path.join(self.output_dir, pair_name)
            os.makedirs(output_folder, exist_ok=True)
            output_path = os.path.join(output_folder, json_filename)
            # Gather strategy insights for JSON export
            # Compute the same values as in the report's strategy section
            bullish_fvgs = self.analysis_results['bullish_fvgs']
            bearish_fvgs = self.analysis_results['bearish_fvgs']
            total_fvgs = bullish_fvgs + bearish_fvgs
            fvg_bias = "BULLISH" if bullish_fvgs > bearish_fvgs else "BEARISH"
            wyckoff_counts = self.analysis_results['wyckoff_phases']
            dominant_phase_num = max(wyckoff_counts, key=wyckoff_counts.get)
            dominant_phase = {1: "Accumulation", 2: "Distribution", 3: "Markup", 4: "Markdown"}.get(dominant_phase_num, str(dominant_phase_num))
            phase_dist = "trending" if max(wyckoff_counts.values()) > total_ticks * 0.4 else "ranging"
            spread_spikes = self.analysis_results['spread_spikes']
            stop_hunts = self.analysis_results['stop_hunts']
            liquidity_sweeps = self.analysis_results['liquidity_sweeps']
            manipulation_score = (spread_spikes + stop_hunts + liquidity_sweeps) / total_ticks * 100
            high_inducements = self.analysis_results['high_inducements']
            low_inducements = self.analysis_results['low_inducements']
            total_inducements = high_inducements + low_inducements
            inducement_rate = (total_inducements / total_ticks) * 100
            market_complexity = "HIGH" if manipulation_score > 5 else "MODERATE" if manipulation_score > 2 else "LOW"

            enriched_results = {
                "summary": {
                    "tick_count": len(self.tick_df),
                    "date_range": {
                        "start": str(self.tick_df['datetime'].min()),
                        "end": str(self.tick_df['datetime'].max())
                    },
                    "price_range": {
                        "min": float(self.tick_df['mid_price'].min()),
                        "max": float(self.tick_df['mid_price'].max())
                    }
                },
                "manipulation": {
                    "spread_spikes": {
                        "count": self.analysis_results['spread_spikes'],
                        "description": "Sharp increases in spread potentially indicating manipulation."
                    },
                    "price_reversals": {
                        "count": self.analysis_results['price_reversals'],
                        "description": "Large price moves in opposite direction after spread spikes."
                    },
                    "stop_hunts": {
                        "count": self.analysis_results['stop_hunts'],
                        "description": "Rapid price movements followed by reversal, indicating potential liquidation events."
                    },
                    "liquidity_sweeps": {
                        "count": self.analysis_results['liquidity_sweeps'],
                        "description": "Price sweeps past previous highs/lows followed by reversal, signaling liquidity collection."
                    }
                },
                "wyckoff": {
                    "phases": {
                        "accumulation": self.analysis_results['wyckoff_phases'][1],
                        "distribution": self.analysis_results['wyckoff_phases'][2],
                        "markup": self.analysis_results['wyckoff_phases'][3],
                        "markdown": self.analysis_results['wyckoff_phases'][4]
                    },
                    "description": "Phase classification based on Wyckoff theory for institutional behavior."
                },
                "smc": {
                    "bullish_fvgs": self.analysis_results['bullish_fvgs'],
                    "bearish_fvgs": self.analysis_results['bearish_fvgs'],
                    "description": "Fair Value Gaps detected per Smart Money Concepts."
                },
                "inducement": {
                    "high": self.analysis_results['high_inducements'],
                    "low": self.analysis_results['low_inducements'],
                    "description": "Trap-like moves above highs or below lows followed by reversal.",
                    "strategy_insights": {
                        "v5_strategy": {
                            "total_fvgs": total_fvgs,
                            "bias": fvg_bias
                        },
                        "v10_strategy": {
                            "dominant_phase": dominant_phase,
                            "phase_distribution": phase_dist
                        },
                        "v12_strategy": {
                            "manipulation_score": manipulation_score,
                            "inducement_rate": inducement_rate,
                            "market_complexity": market_complexity
                        }
                    }
                }
            }
            with open(output_path, "w") as f:
                json.dump(enriched_results, f, indent=4)
            print(f"📝 JSON export saved at: {output_path}")
        return True

# Main execution
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ZANFLOW v12 Microstructure Analysis System – CLI")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--file", help="Single tick CSV/TSV file to analyse")
    group.add_argument("--folder", help="Folder containing one or more tick files")
    parser.add_argument("--limit", type=int, help="Limit number of ticks loaded from each file")
    parser.add_argument("--json", action="store_true", help="Export analysis_results dict to JSON")
    parser.add_argument("--no-dashboard", action="store_true", help="Skip dashboard generation")
    parser.add_argument("--output-dir", type=str, default=".", help="Directory for saving reports / exports")

    args = parser.parse_args()

    print("ZANFLOW v12 Microstructure Analysis System")
    print("==========================================")

    if args.folder:
        files = [f for f in os.listdir(args.folder) if f.endswith(".csv") or f.endswith(".tsv")]
        for file in files:
            print(f"\nAnalyzing: {file}")
            analyzer = MicrostructureAnalyzer(
                os.path.join(args.folder, file),
                limit_ticks=args.limit,
                export_json=args.json,
                no_dashboard=args.no_dashboard,
                output_dir=args.output_dir
            )
            analyzer.run_full_analysis()
    else:
        analyzer = MicrostructureAnalyzer(
            args.file,
            limit_ticks=args.limit,
            export_json=args.json,
            no_dashboard=args.no_dashboard,
            output_dir=args.output_dir
        )
        success = analyzer.run_full_analysis()

        if success:
            print("\n✅ Analysis completed successfully!")
            dashboard_filename = getattr(analyzer, "dashboard_filename", None)
            if dashboard_filename:
                print(f"📊 Dashboard saved as '{dashboard_filename}'")
            else:
                print("📊 Dashboard saved.")
            print("📋 Full report displayed above")
        else:
            print("\n❌ Analysis failed. Please check your data file.")
	