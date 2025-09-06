# Create technical analysis module
#technical_analysis = '''"""
#Technical Analysis Module
#Calculates various technical indicators and patterns#
#"""

import pandas as pd
import numpy as np
import ta

class TechnicalAnalysis:
    def __init__(self):
        self.indicators = {}
        self.calculate_indicators = self.calculate_all

    def calculate_all(self, df):
        """Calculate all technical indicators"""
        if df.empty or df['close'].nunique() <= 1:
            return {}
        if not isinstance(df, pd.DataFrame):
            return {}
        results = {}

        # Trend indicators
        results['sma_20'] = ta.trend.sma_indicator(df['close'], window=20)
        results['sma_50'] = ta.trend.sma_indicator(df['close'], window=50)
        results['sma_200'] = ta.trend.sma_indicator(df['close'], window=200)
        results['ema_20'] = ta.trend.ema_indicator(df['close'], window=20)
        results['ema_50'] = ta.trend.ema_indicator(df['close'], window=50)

        # MACD
        macd = ta.trend.MACD(df['close'])
        results['macd'] = macd.macd()
        results['macd_signal'] = macd.macd_signal()
        results['macd_diff'] = macd.macd_diff()

        # RSI
        results['rsi'] = ta.momentum.RSIIndicator(df['close']).rsi()

        # Bollinger Bands
        bb = ta.volatility.BollingerBands(df['close'])
        results['bb_upper'] = bb.bollinger_hband()
        results['bb_middle'] = bb.bollinger_mavg()
        results['bb_lower'] = bb.bollinger_lband()
        results['bb_width'] = bb.bollinger_wband()

        # ATR
        results['atr'] = ta.volatility.AverageTrueRange(df['high'], df['low'], df['close']).average_true_range()

        # Volume indicators
        results['volume_sma'] = ta.trend.sma_indicator(df['volume'], window=20)
        results['mfi'] = ta.volume.MFIIndicator(df['high'], df['low'], df['close'], df['volume']).money_flow_index()

        # Support and Resistance
        results['support_resistance'] = self.calculate_support_resistance(df)

        # Pivot Points
        results['pivots'] = self.calculate_pivot_points(df)

        # Pattern Recognition
        results['patterns'] = self.detect_candlestick_patterns(df)

        return results

    def calculate_support_resistance(self, df, window=20, num_levels=5):
        """Calculate support and resistance levels"""
        levels = []

        # Find local highs and lows
        highs = df['high'].rolling(window=window, center=True).max() == df['high']
        lows = df['low'].rolling(window=window, center=True).min() == df['low']

        # Extract levels
        resistance_levels = df.loc[highs, 'high'].values
        support_levels = df.loc[lows, 'low'].values

        # Cluster nearby levels
        all_levels = np.concatenate([resistance_levels, support_levels])
        if len(all_levels) > 0:
            clustered = self._cluster_levels(all_levels, threshold=0.001)
            levels = sorted(clustered, reverse=True)[:num_levels]

        return {
            'resistance': [l for l in levels if l > df['close'].iloc[-1]],
            'support': [l for l in levels if l < df['close'].iloc[-1]]
        }

    def _cluster_levels(self, levels, threshold=0.001):
        """Cluster nearby price levels"""
        if len(levels) == 0:
            return []

        sorted_levels = np.sort(levels)
        clusters = []
        current_cluster = [sorted_levels[0]]

        for level in sorted_levels[1:]:
            if (level - current_cluster[-1]) / current_cluster[-1] < threshold:
                current_cluster.append(level)
            else:
                clusters.append(np.mean(current_cluster))
                current_cluster = [level]

        clusters.append(np.mean(current_cluster))
        return clusters

    def calculate_pivot_points(self, df):
        """Calculate pivot points"""
        # Get previous day's data
        high = df['high'].iloc[-1]
        low = df['low'].iloc[-1]
        close = df['close'].iloc[-1]

        # Calculate pivot point
        pp = (high + low + close) / 3

        # Calculate support and resistance levels
        r1 = 2 * pp - low
        r2 = pp + (high - low)
        r3 = high + 2 * (pp - low)

        s1 = 2 * pp - high
        s2 = pp - (high - low)
        s3 = low - 2 * (high - pp)

        return {
            'pp': pp,
            'r1': r1, 'r2': r2, 'r3': r3,
            's1': s1, 's2': s2, 's3': s3
        }

    def detect_candlestick_patterns(self, df):
        """Detect common candlestick patterns"""
        patterns = []

        # Calculate pattern indicators
        open_prices = df['open'].values
        high_prices = df['high'].values
        low_prices = df['low'].values
        close_prices = df['close'].values

        # Doji
        body_size = abs(close_prices - open_prices)
        total_range = high_prices - low_prices
        total_range[total_range == 0] = np.nan
        doji = body_size < (0.1 * total_range)
        
        # Hammer
        lower_shadow = np.minimum(open_prices, close_prices) - low_prices
        upper_shadow = high_prices - np.maximum(open_prices, close_prices)
        hammer = (lower_shadow > 2 * body_size) & (upper_shadow < body_size)
        
        # Engulfing
        bullish_engulfing = (
                (close_prices[1:] > open_prices[1:]) &
                (close_prices[:-1] < open_prices[:-1]) &
                (open_prices[1:] < close_prices[:-1]) &
                (close_prices[1:] > open_prices[:-1])
        )
        
        # Store detected patterns
        for i in range(len(df)):
            if i < len(doji) and doji[i]:
                patterns.append({'index': i, 'pattern': 'Doji', 'position': df.index[i]})
            if i < len(hammer) and hammer[i]:
                patterns.append({'index': i, 'pattern': 'Hammer', 'position': df.index[i]})
            if i > 0 and i-1 < len(bullish_engulfing) and bullish_engulfing[i-1]:
                patterns.append({'index': i, 'pattern': 'Bullish Engulfing', 'position': df.index[i]})
        
        return patterns
    
    def mtf_confluence_analysis(self, timeframes_dict, selected_tfs):
        """Analyze confluence across multiple timeframes"""
        confluence = {
            'trends': {},
            'key_levels': {'resistance': [], 'support': []},
            'momentum': {},
            'signals': []
        }
        
        for tf in selected_tfs:
            if tf not in timeframes_dict:
                continue
            
            df = timeframes_dict[tf]
            
            # Trend analysis
            sma_20 = ta.trend.sma_indicator(df['close'], window=20)
            sma_50 = ta.trend.sma_indicator(df['close'], window=50)
            
            if len(sma_20) > 0 and len(sma_50) > 0:
                current_price = df['close'].iloc[-1]
                if current_price > sma_20.iloc[-1] and sma_20.iloc[-1] > sma_50.iloc[-1]:
                    confluence['trends'][tf] = 'Bullish'
                elif current_price < sma_20.iloc[-1] and sma_20.iloc[-1] < sma_50.iloc[-1]:
                    confluence['trends'][tf] = 'Bearish'
                else:
                    confluence['trends'][tf] = 'Neutral'
            
            # Key levels
            sr_levels = self.calculate_support_resistance(df)
            confluence['key_levels']['resistance'].extend(sr_levels['resistance'])
            confluence['key_levels']['support'].extend(sr_levels['support'])
            
            # Momentum
            rsi = ta.momentum.RSIIndicator(df['close']).rsi()
            if len(rsi) > 0:
                confluence['momentum'][tf] = {
                    'rsi': rsi.iloc[-1],
                    'overbought': rsi.iloc[-1] > 70,
                    'oversold': rsi.iloc[-1] < 30
                }
        
        # Cluster key levels across timeframes
        confluence['key_levels']['resistance'] = self._cluster_levels(
            confluence['key_levels']['resistance']
        )[:5]
        confluence['key_levels']['support'] = self._cluster_levels(
            confluence['key_levels']['support']
        )[:5]
        
        return confluence
