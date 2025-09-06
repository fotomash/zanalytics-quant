# Create Analysis Panel component
#analysis_panel = '''"""
#Analysis Panel Component
#Displays analysis results in organized panels
#"""

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
