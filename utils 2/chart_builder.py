# Create Chart Builder component
# chart_builder = '''"""
# Chart Builder Component
# Creates interactive Plotly charts for the dashboard
# """

import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np

class ChartBuilder:
    def __init__(self):
        self.color_scheme = {
            'bullish': '#26a69a',
            'bearish': '#ef5350',
            'neutral': '#7f8c8d',
            'background': '#1e1e1e',
            'grid': '#2c2c2c',
            'text': '#ffffff'
        }
    
    def create_main_chart(self, df, timeframe, chart_type='Candlestick', 
                         show_volume=True, analysis_results=None):
        """Create the main analysis chart"""
        
        # Determine number of subplots
        rows = 3 if show_volume else 2
        row_heights = [0.6, 0.2, 0.2] if show_volume else [0.7, 0.3]
        
        # Create subplots
        fig = make_subplots(
            rows=rows, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.03,
            row_heights=row_heights,
            subplot_titles=(f'{timeframe} Price Chart', 'Volume', 'RSI') if show_volume else (f'{timeframe} Price Chart', 'RSI')
        )
        
        # Add price chart
        if chart_type == 'Candlestick':
            fig.add_trace(
                go.Candlestick(
                    x=df.index,
                    open=df['open'],
                    high=df['high'],
                    low=df['low'],
                    close=df['close'],
                    name='Price',
                    increasing_line_color=self.color_scheme['bullish'],
                    decreasing_line_color=self.color_scheme['bearish']
                ),
                row=1, col=1
            )
        elif chart_type == 'Heikin Ashi':
            ha_df = self._calculate_heikin_ashi(df)
            fig.add_trace(
                go.Candlestick(
                    x=ha_df.index,
                    open=ha_df['ha_open'],
                    high=ha_df['ha_high'],
                    low=ha_df['ha_low'],
                    close=ha_df['ha_close'],
                    name='Heikin Ashi',
                    increasing_line_color=self.color_scheme['bullish'],
                    decreasing_line_color=self.color_scheme['bearish']
                ),
                row=1, col=1
            )
        else:  # Line chart
            fig.add_trace(
                go.Scatter(
                    x=df.index,
                    y=df['close'],
                    mode='lines',
                    name='Close Price',
                    line=dict(color=self.color_scheme['bullish'], width=2)
                ),
                row=1, col=1
            )
        
        # Add analysis overlays if available
        if analysis_results:
            self._add_analysis_overlays(fig, df, analysis_results)
        
        # Add volume
        if show_volume:
            colors = [self.color_scheme['bullish'] if close >= open else self.color_scheme['bearish'] 
                     for close, open in zip(df['close'], df['open'])]
            
            fig.add_trace(
                go.Bar(
                    x=df.index,
                    y=df['volume'],
                    name='Volume',
                    marker_color=colors,
                    opacity=0.7
                ),
                row=2, col=1
            )
        
        # Add RSI
        if 'indicators' in analysis_results and 'rsi' in analysis_results['indicators']:
            rsi = analysis_results['indicators']['rsi']
            
            fig.add_trace(
                go.Scatter(
                    x=df.index,
                    y=rsi,
                    mode='lines',
                    name='RSI',
                    line=dict(color='#ff9800', width=2)
                ),
                row=rows, col=1
            )
            
            # Add RSI levels
            fig.add_hline(y=70, line_dash="dash", line_color="red", opacity=0.5, row=rows, col=1)
            fig.add_hline(y=30, line_dash="dash", line_color="green", opacity=0.5, row=rows, col=1)
        
        # Update layout
        fig.update_layout(
            title=f"{timeframe} Analysis Chart",
            xaxis_title="Time",
            yaxis_title="Price",
            template="plotly_dark",
            height=800,
            showlegend=True,
            legend=dict(
                yanchor="top",
                y=0.99,
                xanchor="left",
                x=0.01
            ),
            margin=dict(l=0, r=0, t=30, b=0)
        )
        
        # Update xaxis
        fig.update_xaxes(
            rangeslider_visible=False,
            type='date'
        )
        
        return fig
    
    def _calculate_heikin_ashi(self, df):
        """Calculate Heikin Ashi candles"""
        ha_df = df.copy()
        
        ha_df['ha_close'] = (df['open'] + df['high'] + df['low'] + df['close']) / 4
        
        ha_df['ha_open'] = (df['open'].shift(1) + df['close'].shift(1)) / 2
        ha_df['ha_open'].iloc[0] = (df['open'].iloc[0] + df['close'].iloc[0]) / 2
        
        ha_df['ha_high'] = ha_df[['high', 'ha_open', 'ha_close']].max(axis=1)
        ha_df['ha_low'] = ha_df[['low', 'ha_open', 'ha_close']].min(axis=1)
        
        return ha_df
    
    def _add_analysis_overlays(self, fig, df, analysis_results):
        """Add analysis overlays to the chart"""
        
        # Add SMC analysis
        if 'smc' in analysis_results:
            smc = analysis_results['smc']
            
            # Add liquidity zones
            for zone in smc.get('liquidity_zones', [])[:10]:
                color = 'rgba(255, 0, 0, 0.2)' if zone['type'] == 'SSL' else 'rgba(0, 255, 0, 0.2)'
                fig.add_hline(
                    y=zone['level'],
                    line_dash="dot",
                    line_color=color.replace('0.2', '0.8'),
                    annotation_text=f"{zone['type']} Liquidity",
                    annotation_position="right",
                    row=1, col=1
                )
            
            # Add order blocks
            for ob in smc.get('order_blocks', [])[:5]:
                color = 'rgba(0, 255, 0, 0.3)' if ob['type'] == 'bullish' else 'rgba(255, 0, 0, 0.3)'
                fig.add_shape(
                    type="rect",
                    x0=df.index[ob['index']],
                    x1=df.index[-1],
                    y0=ob['start'],
                    y1=ob['end'],
                    fillcolor=color,
                    line=dict(width=0),
                    row=1, col=1
                )
            
            # Add fair value gaps
            for fvg in smc.get('fair_value_gaps', [])[:5]:
                if not fvg['filled']:
                    color = 'rgba(255, 255, 0, 0.2)'
                    fig.add_shape(
                        type="rect",
                        x0=df.index[fvg['index']],
                        x1=df.index[-1],
                        y0=fvg['bottom'],
                        y1=fvg['top'],
                        fillcolor=color,
                        line=dict(color='yellow', width=1),
                        row=1, col=1
                    )
        
        # Add Wyckoff events
        if 'wyckoff' in analysis_results:
            wyckoff = analysis_results['wyckoff']
            
            for event in wyckoff.get('events', [])[:10]:
                fig.add_annotation(
                    x=event['time'],
                    y=event['price'],
                    text=event['type'],
                    showarrow=True,
                    arrowhead=2,
                    arrowsize=1,
                    arrowwidth=2,
                    arrowcolor="#ffffff",
                    ax=0,
                    ay=-40,
                    bgcolor="rgba(0, 0, 0, 0.8)",
                    bordercolor="#ffffff",
                    borderwidth=1,
                    font=dict(color="#ffffff", size=10),
                    row=1, col=1
                )
        
        # Add technical indicators
        if 'indicators' in analysis_results:
            indicators = analysis_results['indicators']
            
            # Add moving averages
            if 'sma_20' in indicators:
                fig.add_trace(
                    go.Scatter(
                        x=df.index,
                        y=indicators['sma_20'],
                        mode='lines',
                        name='SMA 20',
                        line=dict(color='#2196f3', width=1),
                        opacity=0.7
                    ),
                    row=1, col=1
                )
            
            if 'sma_50' in indicators:
                fig.add_trace(
                    go.Scatter(
                        x=df.index,
                        y=indicators['sma_50'],
                        mode='lines',
                        name='SMA 50',
                        line=dict(color='#ff9800', width=1),
                        opacity=0.7
                    ),
                    row=1, col=1
                )
            
            # Add Bollinger Bands
            if all(k in indicators for k in ['bb_upper', 'bb_middle', 'bb_lower']):
                fig.add_trace(
                    go.Scatter(
                        x=df.index,
                        y=indicators['bb_upper'],
                        mode='lines',
                        name='BB Upper',
                        line=dict(color='rgba(128, 128, 128, 0.5)', width=1)
                    ),
                    row=1, col=1
                )
                
                fig.add_trace(
                    go.Scatter(
                        x=df.index,
                        y=indicators['bb_lower'],
                        mode='lines',
                        name='BB Lower',
                        line=dict(color='rgba(128, 128, 128, 0.5)', width=1),
                        fill='tonexty',
                        fillcolor='rgba(128, 128, 128, 0.1)'
                    ),
                    row=1, col=1
                )
    
    def create_mtf_chart(self, timeframes_dict, selected_tfs):
        """Create multi-timeframe comparison chart"""
        
        rows = len(selected_tfs)
        fig = make_subplots(
            rows=rows, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.02,
            subplot_titles=selected_tfs
        )
        
        for i, tf in enumerate(selected_tfs):
            if tf in timeframes_dict:
                df = timeframes_dict[tf]
                
                # Add candlestick chart
                fig.add_trace(
                    go.Candlestick(
                        x=df.index,
                        open=df['open'],
                        high=df['high'],
                        low=df['low'],
                        close=df['close'],
                        name=f'{tf} Price',
                        increasing_line_color=self.color_scheme['bullish'],
                        decreasing_line_color=self.color_scheme['bearish'],
                        showlegend=False
                    ),
                    row=i+1, col=1
                )
                
                # Add SMA
                sma_period = min(20, len(df) // 2)
                if sma_period > 1:
                    sma = df['close'].rolling(window=sma_period).mean()
                    fig.add_trace(
                        go.Scatter(
                            x=df.index,
                            y=sma,
                            mode='lines',
                            name=f'{tf} SMA{sma_period}',
                            line=dict(color='#2196f3', width=1),
                            showlegend=False
                        ),
                        row=i+1, col=1
                    )
        
        # Update layout
        fig.update_layout(
            title="Multi-Timeframe Analysis",
            template="plotly_dark",
            height=250 * rows,
            showlegend=False,
            margin=dict(l=0, r=0, t=30, b=0)
        )
        
        # Update all xaxes
        fig.update_xaxes(rangeslider_visible=False)
        
        return fig
    
    def create_volume_profile_chart(self, df, volume_profile_data):
        """Create volume profile visualization"""
        
        fig = make_subplots(
            rows=1, cols=2,
            column_widths=[0.8, 0.2],
            shared_yaxes=True,
            horizontal_spacing=0.01
        )
        
        # Add candlestick chart
        fig.add_trace(
            go.Candlestick(
                x=df.index,
                open=df['open'],
                high=df['high'],
                low=df['low'],
                close=df['close'],
                name='Price',
                increasing_line_color=self.color_scheme['bullish'],
                decreasing_line_color=self.color_scheme['bearish']
            ),
            row=1, col=1
        )
        
        # Add volume profile
        if volume_profile_data and 'profile' in volume_profile_data:
            profile = volume_profile_data['profile']
            
            fig.add_trace(
                go.Bar(
                    x=profile['volume'],
                    y=profile['price'],
                    orientation='h',
                    name='Volume Profile',
                    marker_color='rgba(33, 150, 243, 0.7)'
                ),
                row=1, col=2
            )
            
            # Add POC line
            if 'poc' in volume_profile_data:
                poc = volume_profile_data['poc']
                fig.add_hline(
                    y=poc['price'],
                    line_dash="solid",
                    line_color="red",
                    line_width=2,
                    annotation_text="POC",
                    annotation_position="right"
                )
            
            # Add value area
            if 'value_area' in volume_profile_data:
                va = volume_profile_data['value_area']
                fig.add_hrect(
                    y0=va['val'],
                    y1=va['vah'],
                    fillcolor="rgba(255, 255, 0, 0.1)",
                    line_width=0
                )
        
        # Update layout
        fig.update_layout(
            title="Volume Profile Analysis",
            template="plotly_dark",
            height=600,
            showlegend=True,
            margin=dict(l=0, r=0, t=30, b=0)
        )
        
        fig.update_xaxes(rangeslider_visible=False, row=1, col=1)
        fig.update_xaxes(showticklabels=False, row=1, col=2)
        
        return fig
'''

with open('zanflow_dashboard/components/chart_builder.py', 'w') as f:
    f.write(chart_builder)
print("Created chart_builder.py")

# Create Analysis Panel component
analysis_panel = '''"""
Analysis Panel Component
Displays analysis results in organized panels
"""

import streamlit as st
import pandas as pd

class AnalysisPanel:
    def __init__(self):
        self.panel_config = {
            'smc': {
                'title': '🏛️ Smart Money Concepts',
                'icon': '🏛️'
            },
            'wyckoff': {
                'title': '📊 Wyckoff Analysis',
                'icon': '📊'
            },
            'volume_profile': {
                'title': '📈 Volume Profile',
                'icon': '📈'
            },
            'indicators': {
                'title': '📉 Technical Indicators',
                'icon': '📉'
            }
        }
    
    def display_results(self, analysis_results):
        """Display all analysis results in organized panels"""
        
        # Create tabs for different analysis types
        tabs = st.tabs([self.panel_config[key]['title'] for key in analysis_results.keys() if key in self.panel_config])
        
        tab_index = 0
        for key, results in analysis_results.items():
            if key not in self.panel_config:
                continue
            
            with tabs[tab_index]:
                self._display_analysis_section(key, results)
            tab_index += 1
    
    def _display_analysis_section(self, analysis_type, results):
        """Display a specific analysis section"""
        
        if analysis_type == 'smc':
            self._display_smc_analysis(results)
        elif analysis_type == 'wyckoff':
            self._display_wyckoff_analysis(results)
        elif analysis_type == 'volume_profile':
            self._display_volume_profile_analysis(results)
        elif analysis_type == 'indicators':
            self._display_indicators_analysis(results)
    
    def _display_smc_analysis(self, results):
        """Display Smart Money Concepts analysis"""
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Liquidity Zones")
            if 'liquidity_zones' in results and results['liquidity_zones']:
                for zone in results['liquidity_zones'][:5]:
                    zone_type = "🔴 Sell-side" if zone['type'] == 'SSL' else "🟢 Buy-side"
                    st.write(f"{zone_type}: ${zone['level']:.5f}")
                    st.progress(zone['strength'])
            else:
                st.info("No significant liquidity zones detected")
            
            st.subheader("Order Blocks")
            if 'order_blocks' in results and results['order_blocks']:
                for ob in results['order_blocks'][:5]:
                    ob_type = "🟢 Bullish" if ob['type'] == 'bullish' else "🔴 Bearish"
                    st.write(f"{ob_type}: ${ob['start']:.5f} - ${ob['end']:.5f}")
                    st.caption(f"Strength: {ob['strength']:.2%}")
            else:
                st.info("No order blocks detected")
        
        with col2:
            st.subheader("Fair Value Gaps")
            if 'fair_value_gaps' in results and results['fair_value_gaps']:
                unfilled_fvgs = [fvg for fvg in results['fair_value_gaps'] if not fvg['filled']]
                if unfilled_fvgs:
                    for fvg in unfilled_fvgs[:5]:
                        fvg_type = "🟢 Bullish" if fvg['type'] == 'bullish' else "🔴 Bearish"
                        st.write(f"{fvg_type} FVG: ${fvg['bottom']:.5f} - ${fvg['top']:.5f}")
                        st.caption(f"Size: {fvg['size']:.5f}")
                else:
                    st.info("All FVGs have been filled")
            else:
                st.info("No fair value gaps detected")
            
            st.subheader("Market Structure")
            if 'market_structure' in results and results['market_structure']:
                latest_break = results['market_structure'][-1] if results['market_structure'] else None
                if latest_break:
                    break_type = "🟢 Bullish" if latest_break['type'] == 'bullish_break' else "🔴 Bearish"
                    st.write(f"Latest: {break_type} structure break")
                    st.write(f"Price: ${latest_break['price']:.5f}")
            else:
                st.info("No structure breaks detected")
    
    def _display_wyckoff_analysis(self, results):
        """Display Wyckoff analysis"""
        
        # Current Phase
        st.subheader("Market Phase")
        if 'current_phase' in results:
            phase = results['current_phase']
            phase_colors = {
                'Accumulation': '🟢',
                'Markup': '🚀',
                'Distribution': '🔴',
                'Markdown': '📉',
                'Transitional': '🟡'
            }
            emoji = phase_colors.get(phase, '❓')
            st.metric("Current Phase", f"{emoji} {phase}")
        
        # Wyckoff Events
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Recent Events")
            if 'events' in results and results['events']:
                events_df = pd.DataFrame(results['events'][-5:])
                for _, event in events_df.iterrows():
                    st.write(f"**{event['type']}** - {event['description']}")
                    st.caption(f"Price: ${event['price']:.5f}")
            else:
                st.info("No Wyckoff events detected")
        
        with col2:
            st.subheader("Springs & Upthrusts")
            if 'spring_upthrust' in results and results['spring_upthrust']:
                for item in results['spring_upthrust'][-3:]:
                    if item['type'] == 'Spring':
                        st.write(f"🟢 **Spring** detected")
                        st.caption(f"Low: ${item['spring_low']:.5f}")
                    else:
                        st.write(f"🔴 **Upthrust** detected")
                        st.caption(f"High: ${item['upthrust_high']:.5f}")
            else:
                st.info("No springs or upthrusts detected")
        
        # Volume Analysis
        st.subheader("Volume Patterns")
        if 'volume_analysis' in results:
            vol_analysis = results['volume_analysis']
            
            if 'effort_vs_result' in vol_analysis and vol_analysis['effort_vs_result']:
                latest_evr = vol_analysis['effort_vs_result'][-1]
                if latest_evr['type'] == 'high_effort_low_result':
                    st.warning("⚠️ High effort with low result detected - potential reversal")
            
            if 'volume_surge' in vol_analysis and vol_analysis['volume_surge']:
                surge_count = len(vol_analysis['volume_surge'])
                st.info(f"📊 {surge_count} volume surges detected")
    
    def _display_volume_profile_analysis(self, results):
        """Display Volume Profile analysis"""
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.subheader("Point of Control")
            if 'poc' in results and results['poc']:
                poc = results['poc']
                st.metric("POC Price", f"${poc['price']:.5f}")
                st.caption(f"Volume: {poc['volume']:,.0f}")
            else:
                st.info("POC not calculated")
        
        with col2:
            st.subheader("Value Area")
            if 'value_area' in results and results['value_area']:
                va = results['value_area']
                st.metric("VAH", f"${va['vah']:.5f}")
                st.metric("VAL", f"${va['val']:.5f}")
                st.caption(f"Contains {va['percentage']:.1%} of volume")
            else:
                st.info("Value area not calculated")
        
        with col3:
            st.subheader("Volume Nodes")
            if 'hvn_lvn' in results and results['hvn_lvn']:
                hvn_lvn = results['hvn_lvn']
                if hvn_lvn['hvn']:
                    st.write("**High Volume Nodes:**")
                    for node in hvn_lvn['hvn'][:3]:
                        st.caption(f"${node['price']:.5f}")
                if hvn_lvn['lvn']:
                    st.write("**Low Volume Nodes:**")
                    for node in hvn_lvn['lvn'][:3]:
                        st.caption(f"${node['price']:.5f}")
            else:
                st.info("No volume nodes identified")
        
        # Naked POCs
        if 'naked_poc' in results and results['naked_poc']:
            st.subheader("Naked POCs")
            for npoc in results['naked_poc']:
                distance = npoc['distance_from_current'] * 100
                st.write(f"Untested POC at ${npoc['price']:.5f} ({distance:.1f}% away)")
    
    def _display_indicators_analysis(self, results):
        """Display Technical Indicators analysis"""
        
        # Current indicator values
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.subheader("Trend Indicators")
            if 'sma_20' in results and len(results['sma_20']) > 0:
                current_price = results.get('current_price', 0)
                sma_20 = results['sma_20'].iloc[-1] if hasattr(results['sma_20'], 'iloc') else results['sma_20'][-1]
                trend = "🟢 Above" if current_price > sma_20 else "🔴 Below"
                st.metric("SMA 20", f"${sma_20:.5f}", trend)
            
            if 'sma_50' in results and len(results['sma_50']) > 0:
                sma_50 = results['sma_50'].iloc[-1] if hasattr(results['sma_50'], 'iloc') else results['sma_50'][-1]
                st.metric("SMA 50", f"${sma_50:.5f}")
        
        with col2:
            st.subheader("Momentum")
            if 'rsi' in results and len(results['rsi']) > 0:
                rsi = results['rsi'].iloc[-1] if hasattr(results['rsi'], 'iloc') else results['rsi'][-1]
                rsi_status = "🔴 Overbought" if rsi > 70 else "🟢 Oversold" if rsi < 30 else "Neutral"
                st.metric("RSI", f"{rsi:.1f}", rsi_status)
            
            if 'macd_diff' in results and len(results['macd_diff']) > 0:
                macd_diff = results['macd_diff'].iloc[-1] if hasattr(results['macd_diff'], 'iloc') else results['macd_diff'][-1]
                macd_trend = "🟢 Bullish" if macd_diff > 0 else "🔴 Bearish"
                st.metric("MACD Histogram", f"{macd_diff:.5f}", macd_trend)
        
        with col3:
            st.subheader("Volatility")
            if 'atr' in results and len(results['atr']) > 0:
                atr = results['atr'].iloc[-1] if hasattr(results['atr'], 'iloc') else results['atr'][-1]
                st.metric("ATR", f"{atr:.5f}")
            
            if 'bb_width' in results and len(results['bb_width']) > 0:
                bb_width = results['bb_width'].iloc[-1] if hasattr(results['bb_width'], 'iloc') else results['bb_width'][-1]
                st.metric("BB Width", f"{bb_width:.5f}")
        
        # Support and Resistance
        if 'support_resistance' in results:
            st.subheader("Support & Resistance Levels")
            sr = results['support_resistance']
            
            col1, col2 = st.columns(2)
            with col1:
                st.write("**Resistance Levels:**")
                for level in sr.get('resistance', [])[:3]:
                    st.caption(f"${level:.5f}")
            
            with col2:
                st.write("**Support Levels:**")
                for level in sr.get('support', [])[:3]:
                    st.caption(f"${level:.5f}")
        
        # Patterns
        if 'patterns' in results and results['patterns']:
            st.subheader("Candlestick Patterns")
            recent_patterns = results['patterns'][-5:]
            for pattern in recent_patterns:
                st.write(f"• {pattern['pattern']} at {pattern['position']}")
'''

with open('zanflow_dashboard/components/analysis_panel.py', 'w') as f:
    f.write(analysis_panel)
print("Created analysis_panel.py")

# Create __init__.py for components
with open('zanflow_dashboard/components/__init__.py', 'w') as f:
    f.write('# Components package')
print("Created components/__init__.py")

# Create a sample data generator for testing
sample_data = '''"""
Sample Data Generator
Creates sample market data for testing the dashboard
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def generate_sample_data(symbol='EURUSD', days=30):
    """Generate sample OHLCV data"""
    
    # Generate timestamps (M1 data)
    end_time = datetime.now()
    start_time = end_time - timedelta(days=days)
    timestamps = pd.date_range(start=start_time, end=end_time, freq='1min')
    
    # Generate price data
    np.random.seed(42)
    num_bars = len(timestamps)
    
    # Random walk for price
    returns = np.random.normal(0, 0.0001, num_bars)
    price = 1.1000
    prices = [price]
    
    for ret in returns[1:]:
        price = price * (1 + ret)
        prices.append(price)
    
    prices = np.array(prices)
    
    # Generate OHLC from price
    data = []
    for i in range(num_bars):
        close = prices[i]
        
        # Add some noise for high/low
        high = close * (1 + abs(np.random.normal(0, 0.0001)))
        low = close * (1 - abs(np.random.normal(0, 0.0001)))
        
        # Open is previous close with small gap
        if i == 0:
            open_price = close * (1 + np.random.normal(0, 0.00005))
        else:
            open_price = data[i-1]['close'] * (1 + np.random.normal(0, 0.00005))
        
        # Ensure OHLC consistency
        high = max(high, open_price, close)
        low = min(low, open_price, close)
        
        # Generate volume (higher during "market hours")
        hour = timestamps[i].hour
        base_volume = 1000
        if 8 <= hour <= 16:  # Market hours
            volume = base_volume * np.random.uniform(1.5, 3.0)
        else:
            volume = base_volume * np.random.uniform(0.5, 1.5)
        
        data.append({
            'datetime': timestamps[i],
            'open': open_price,
            'high': high,
            'low': low,
            'close': close,
            'volume': int(volume)
        })
    
    # Create DataFrame
    df = pd.DataFrame(data)
    
    # Save as tab-separated file
    filename = f'./data/{symbol}_M1_sample.csv'
    df.to_csv(filename, sep='\\t', index=False)
    
    return filename

if __name__ == "__main__":
    # Generate sample data
    filename = generate_sample_data()
    print(f"Sample data generated: {filename}")
'''

with open('zanflow_dashboard/generate_sample_data.py', 'w') as f:
    f.write(sample_data)
print("Created generate_sample_data.py")

# Create README for the dashboard
readme = '''# Zanflow Multi-Timeframe Analysis Dashboard

A comprehensive Streamlit dashboard for institutional-grade market analysis using Smart Money Concepts, Wyckoff methodology, and advanced technical analysis.

## Features

- **Multi-Timeframe Analysis**: Automatically upsample M1 data to all available timeframes
- **Smart Money Concepts**: Liquidity zones, order blocks, fair value gaps, market structure
- **Wyckoff Analysis**: Phase identification, springs/upthrusts, volume analysis
- **Volume Profile**: POC, value areas, HVN/LVN identification
- **Technical Indicators**: Moving averages, RSI, MACD, Bollinger Bands, and more
- **Interactive Charts**: Plotly-based charts with overlays and annotations
- **Real-time Analysis**: Process and visualize data as it's loaded

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt