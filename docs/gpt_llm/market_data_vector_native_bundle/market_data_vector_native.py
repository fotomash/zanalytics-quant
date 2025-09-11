# market_data_vector_native.py

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import io
import base64
from datetime import datetime, timedelta

class MarketDataVectorNative:
    def __init__(self):
        self.assets = ['BTC', 'ETH', 'SP500', 'FTSE', 'NASDAQ', 'DOW', 'GOLD', 'OIL']
        self.asset_names = {
            'BTC': 'Bitcoin', 'ETH': 'Ethereum', 'SP500': 'S&P 500',
            'FTSE': 'FTSE 100', 'NASDAQ': 'NASDAQ', 'DOW': 'Dow Jones',
            'GOLD': 'Gold', 'OIL': 'Crude Oil'
        }
        self.asset_profiles = {
            'BTC': {'start_price': 60000, 'daily_return': 0.002, 'volatility': 0.03, 'current': 105556.00, 'change': 1111.00},
            'ETH': {'start_price': 1500, 'daily_return': 0.0015, 'volatility': 0.035, 'current': 2521.07, 'change': 45.47},
            'SP500': {'start_price': 4500, 'daily_return': 0.0007, 'volatility': 0.012, 'current': 5321.45, 'change': 14.37},
            'FTSE': {'start_price': 8000, 'daily_return': 0.0005, 'volatility': 0.01, 'current': 8811.04, 'change': 14.10},
            'NASDAQ': {'start_price': 14000, 'daily_return': 0.0008, 'volatility': 0.018, 'current': 16209.34, 'change': 121.57},
            'DOW': {'start_price': 36000, 'daily_return': 0.0006, 'volatility': 0.011, 'current': 42582.68, 'change': 447.33},
            'GOLD': {'start_price': 2000, 'daily_return': 0.0003, 'volatility': 0.008, 'current': 2387.15, 'change': 12.45},
            'OIL': {'start_price': 80, 'daily_return': 0.0004, 'volatility': 0.02, 'current': 83.27, 'change': -1.23}
        }

    def generate_market_data(self, symbol, days=180):
        profile = self.asset_profiles.get(symbol)
        np.random.seed(42 + sum(ord(c) for c in symbol))
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        dates = pd.date_range(start=start_date, end=end_date, freq='D')
        prices = [profile['start_price']]
        for _ in range(1, len(dates)):
            change_pct = np.random.normal(profile['daily_return'], profile['volatility'])
            prices.append(prices[-1] * (1 + change_pct))
        prices[-1] = profile['current']
        prices[-2] = profile['current'] - profile['change']
        df = pd.DataFrame({'timestamp': dates, 'close': prices}).set_index('timestamp')
        df['returns'] = df['close'].pct_change()
        return df

    def calculate_indicators(self, df):
        delta = df['close'].diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        avg_gain = gain.rolling(window=14).mean()
        avg_loss = loss.rolling(window=14).mean()
        rs = avg_gain / avg_loss
        df['rsi_14'] = 100 - (100 / (1 + rs))
        ema_12 = df['close'].ewm(span=12, adjust=False).mean()
        ema_26 = df['close'].ewm(span=26, adjust=False).mean()
        df['macd'] = ema_12 - ema_26
        df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
        return df

    def create_summary(self, assets=None, days=180):
        if assets is None:
            assets = self.assets
        market_data = []
        price_data = {}
        for asset in assets:
            df = self.generate_market_data(asset, days)
            df = self.calculate_indicators(df)
            latest = df.iloc[-1]
            price = latest['close']
            change_pct = (price - df.iloc[-2]['close']) / df.iloc[-2]['close'] * 100
            rsi = latest['rsi_14']
            macd = latest['macd']
            macd_signal = latest['macd_signal']
            macd_status = "Bullish" if macd > macd_signal else "Bearish"
            recommendation = "Buy" if macd > macd_signal else "Sell"
            volatility = df['returns'].tail(30).std() * np.sqrt(252) * 100
            market_data.append({
                'asset': f"{self.asset_names[asset]} ({asset})",
                'price': round(price, 2),
                'change_percent': round(change_pct, 2),
                'rsi': round(rsi, 1),
                'macd_signal': macd_status,
                'recommendation': recommendation,
                'volatility': round(volatility, 1)
            })
            price_data[self.asset_names[asset]] = df['close']

        # Create markdown table
        md_table = "| Asset | Price | Change % | RSI | MACD Signal | Recommendation | Volatility |
"
        md_table += "|-------|-------|----------|-----|-------------|----------------|------------|
"
        for d in market_data:
            md_table += f"| {d['asset']} | ${d['price']:,} | {d['change_percent']}% | {d['rsi']} | {d['macd_signal']} | {d['recommendation']} | {d['volatility']}% |
"

        # Correlation heatmap
        df_prices = pd.DataFrame(price_data)
        corr = df_prices.pct_change().dropna().corr()

        plt.figure(figsize=(10, 8))
        mask = np.triu(np.ones_like(corr, dtype=bool))
        cmap = sns.diverging_palette(230, 20, as_cmap=True)
        sns.heatmap(corr, mask=mask, cmap=cmap, vmax=1, vmin=-1, center=0,
                    square=True, linewidths=.5, cbar_kws={"shrink": .5}, annot=True, fmt=".2f")
        plt.title("Asset Correlation Heatmap (Daily Returns)")
        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight')
        plt.close()
        buf.seek(0)
        img_base64 = base64.b64encode(buf.read()).decode('utf-8')

        summary_text = f"Market summary generated for {len(assets)} assets."

        return {
            "timestamp": datetime.now().isoformat(),
            "summary": summary_text,
            "data_points": market_data,
            "visualization": {
                "table_markdown": md_table,
                "chart_image_base64": img_base64
            },
            "next_steps": {
                "immediate": ["View asset details", "Analyze correlation matrix"],
                "user_options": ["Change timeframe", "Add/remove assets"],
                "data_refresh": "Every 15 minutes"
            }
        }
