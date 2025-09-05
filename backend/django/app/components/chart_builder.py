import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np

# ===== Unified Dashboard Styling =====
CHART_THEME = "plotly_dark"
BG_COLOR = "rgba(0,0,0,0.02)"
FONT_COLOR = "white"
CANDLE_UP_COLOR = "lime"
CANDLE_DOWN_COLOR = "red"

def apply_dashboard_style(fig, title=None, height=800):
    """Apply consistent dark style used in Home.py"""
    fig.update_layout(
        template=CHART_THEME,
        paper_bgcolor=BG_COLOR,
        plot_bgcolor=BG_COLOR,
        font=dict(color=FONT_COLOR),
        height=height,
        showlegend=False,
        margin=dict(l=20, r=20, t=40, b=20)
    )
    if title:
        fig.update_layout(
            title={
                "text": title,
                "x": 0.5,
                "xanchor": "center",
                "y": 0.95,
                "yanchor": "top"
            }
        )
    # Remove default grid & rangeslider
    fig.update_xaxes(showgrid=False, rangeslider_visible=False)
    fig.update_yaxes(showgrid=False)
    return fig

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
                    increasing_line_color=CANDLE_UP_COLOR,
                    decreasing_line_color=CANDLE_DOWN_COLOR
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
                    increasing_line_color=CANDLE_UP_COLOR,
                    decreasing_line_color=CANDLE_DOWN_COLOR
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
                    line=dict(color=CANDLE_UP_COLOR, width=2)
                ),
                row=1, col=1
            )

        # Add analysis overlays if available
        if analysis_results:
            self._add_analysis_overlays(fig, df, analysis_results)

        # Add volume
        if show_volume:
            colors = [CANDLE_UP_COLOR if close >= open else CANDLE_DOWN_COLOR
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

        fig = apply_dashboard_style(fig, title=f"{timeframe} Analysis Chart", height=800)

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

        # NOTE: overlays now use smooth translucent bands matching Home.py styling

        # Add SMC analysis
        if 'smc' in analysis_results:
            smc = analysis_results['smc']

            # Liquidity zones: shaded horizontal bands (Home.py style)
            for zone in smc.get('liquidity_zones', [])[:10]:
                # soft tinted band
                band_color = (
                    'rgba(255, 0, 0, 0.05)' if zone['type'] == 'SSL'
                    else 'rgba(0, 255, 0, 0.05)'
                )
                std = df['close'].std()
                fig.add_shape(
                    type="rect",
                    x0=df.index[0],
                    x1=df.index[-1],
                    y0=zone['level'] - std * 0.15,
                    y1=zone['level'] + std * 0.15,
                    fillcolor=band_color,
                    opacity=0.05,
                    line=dict(width=0),
                    layer="below",
                    row=1, col=1
                )

            # Add order blocks
            for ob in smc.get('order_blocks', [])[:5]:
                color = 'rgba(0, 255, 0, 0.05)' if ob['type'] == 'bullish' else 'rgba(255, 0, 0, 0.05)'
                fig.add_shape(
                    type="rect",
                    x0=df.index[ob['index']],
                    x1=df.index[-1],
                    y0=ob['start'],
                    y1=ob['end'],
                    fillcolor=color,
                    line=dict(width=1, dash="dot", color=color.replace('0.05', '0.5')),
                    layer="below",
                    row=1, col=1
                )

            # Add fair value gaps
            for fvg in smc.get('fair_value_gaps', [])[:5]:
                if not fvg['filled']:
                    color = 'rgba(255,255,0,0.07)'
                    fig.add_shape(
                        type="rect",
                        x0=df.index[fvg['index']],
                        x1=df.index[-1],
                        y0=fvg['bottom'],
                        y1=fvg['top'],
                        fillcolor=color,
                        line=dict(color='yellow', width=1, dash='dot'),
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
                        increasing_line_color=CANDLE_UP_COLOR,
                        decreasing_line_color=CANDLE_DOWN_COLOR,
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

        fig = apply_dashboard_style(fig, title="Multi-Timeframe Analysis", height=250 * rows)

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
                increasing_line_color=CANDLE_UP_COLOR,
                decreasing_line_color=CANDLE_DOWN_COLOR
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

        fig = apply_dashboard_style(fig, title="Volume Profile Analysis", height=600)

        fig.update_xaxes(showticklabels=False, row=1, col=2)
        
        return fig