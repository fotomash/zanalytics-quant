
import os
import json
import pickle
import hashlib
import logging
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import yfinance as yf
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from fredapi import Fred
from openai import OpenAI
import requests
import warnings
import time
warnings.filterwarnings('ignore')

# Utility to embed images as base64 for CSS backgrounds
import base64

def get_base64_image(path):
    with open(path, "rb") as f:
        data = f.read()
    return base64.b64encode(data).decode()

# Enhanced Professional Trading Dashboard

# QRT Quant-Style Trading Desk Analysis System

import os
import json
import pickle
import hashlib
import logging
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import yfinance as yf
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from fredapi import Fred
from openai import OpenAI
import requests
import warnings
warnings.filterwarnings('ignore')

# Configure page
st.set_page_config(
    page_title="Macro Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Streamlit CSS: background + panel styling with base64-embedded image
img_base64 = get_base64_image("./pages/image_af247b.jpg")

# --- COPIED CSS BLOCK FROM Home.py for background, container, and card opacity ---
st.markdown(f"""
<style>
    .stApp {{
        background-image: url("data:image/jpg;base64,{img_base64}");
        background-size: cover;
        background-attachment: fixed;
        background-position: center;
    }}
    .main, .block-container {{
        background: rgba(14, 17, 23, 0.88) !important;
        border-radius: 16px;
        padding: 2.2rem 2.4rem;
        box-shadow: 0 4px 32px 0 rgba(12,10,30,0.16);
    }}
    .market-card {{
        background: rgba(28, 28, 32, 0.83);
        border-radius: 14px;
        padding: 24px 24px 14px 24px;
        border: 1.4px solid rgba(255,255,255,0.09);
        margin-bottom: 24px;
        box-shadow: 0 2px 14px 0 rgba(0,0,0,0.23);
    }}
</style>
""", unsafe_allow_html=True)

# Initialize clients
logging.basicConfig(level=logging.INFO)
client = OpenAI(api_key=st.secrets.get("openai_API"))
fred = Fred(api_key=st.secrets.get("fred_api_key", "6a980b8c2421503564570ecf4d765173"))

# Professional asset mapping
PROFESSIONAL_SYMBOL_MAP = {
    # FX Majors
    "dxy_quote": "DX-Y.NYB",
    "eurusd_quote": "EURUSD=X",
    "gbpusd_quote": "GBPUSD=X",
    "usdjpy_quote": "USDJPY=X",
    "audusd_quote": "AUDUSD=X",
    "usdcad_quote": "USDCAD=X",
    "usdchf_quote": "USDCHF=X",
    "nzdusd_quote": "NZDUSD=X",
    "eurgbp_quote": "EURGBP=X",

    # Volatility
    "vix_quote": "^VIX",
    "vvix_quote": "^VVIX",
    "ovx_quote": "^OVX",
    "gvz_quote": "^GVZ",

    # Commodities
    "gold_quote": "GC=F",
    "silver_quote": "SI=F",
    "oil_quote": "CL=F",
    "natgas_quote": "NG=F",
    "copper_quote": "HG=F",

    # Yields (will use FRED)
    "us10y_quote": "^TNX",
    "us2y_quote": "^IRX",
    "us30y_quote": "^TYX",
    "de10y_quote": "DE10Y-DE.BE",
    "uk10y_quote": "GB10Y-GB.BE",
    "jp10y_quote": "JP10Y-JP.BE",

    # Indices
    "spx_quote": "^GSPC",
    "nasdaq_quote": "^IXIC",
    "dji_quote": "^DJI",
    "rut_quote": "^RUT",
    "dax_quote": "^GDAXI",
    "ftse_quote": "^FTSE",
    "nikkei_quote": "^N225",
    "hsi_quote": "^HSI",

    # Crypto
    "btc_quote": "BTC-USD",
    "eth_quote": "ETH-USD"
}

# Enhanced display names
ENHANCED_DISPLAY_NAMES = {
    'dxy_quote': 'DXY',
    'eurusd_quote': 'EUR/USD',
    'gbpusd_quote': 'GBP/USD',
    'usdjpy_quote': 'USD/JPY',
    'audusd_quote': 'AUD/USD',
    'usdcad_quote': 'USD/CAD',
    'usdchf_quote': 'USD/CHF',
    'nzdusd_quote': 'NZD/USD',
    'eurgbp_quote': 'EUR/GBP',
    'vix_quote': 'VIX',
    'vvix_quote': 'VVIX',
    'ovx_quote': 'OVX (Oil VIX)',
    'gvz_quote': 'GVZ (Gold VIX)',
    'gold_quote': 'Gold',
    'silver_quote': 'Silver',
    'oil_quote': 'WTI Crude',
    'natgas_quote': 'Natural Gas',
    'copper_quote': 'Copper',
    'us10y_quote': 'US 10Y',
    'us2y_quote': 'US 2Y',
    'us30y_quote': 'US 30Y',
    'de10y_quote': 'DE 10Y',
    'uk10y_quote': 'UK 10Y',
    'jp10y_quote': 'JP 10Y',
    'spx_quote': 'S&P 500',
    'nasdaq_quote': 'NASDAQ',
    'dji_quote': 'Dow Jones',
    'rut_quote': 'Russell 2000',
    'dax_quote': 'DAX',
    'ftse_quote': 'FTSE 100',
    'nikkei_quote': 'Nikkei',
    'hsi_quote': 'Hang Seng',
    'btc_quote': 'Bitcoin',
    'eth_quote': 'Ethereum'
}

# Price validation thresholds
PRICE_THRESHOLDS = {
    "dxy_quote": (90, 120),
    "vix_quote": (10, 80),
    "gold_quote": (1500, 3000),
    "oil_quote": (20, 150),
    "us10y_quote": (0, 10),
    "de10y_quote": (-1, 10),
    "uk10y_quote": (0, 10),
    "gbpusd_quote": (1.0, 1.6),
    "eurusd_quote": (0.9, 1.5),
    "usdjpy_quote": (100, 160),
    "spx_quote": (3000, 6000),
    "nasdaq_quote": (10000, 20000),
    "btc_quote": (10000, 100000)
}

# Cache directory setup
def ensure_cache_dir():
    os.makedirs(".cache", exist_ok=True)
    os.makedirs(".cache/prices", exist_ok=True)
    os.makedirs(".cache/news", exist_ok=True)
    os.makedirs(".cache/analysis", exist_ok=True)

ensure_cache_dir()

# Cache TTL for price fetches
CACHE_TTL_SEC = 300  # 5‑minute disk cache for price fetches

@st.cache_data
def get_validated_prices(symbol_map):
    """
    Fetch prices with professional-grade validation, using a 5-minute disk cache.
    Returns: (prices, errors, last_updated: datetime)
    """
    import hashlib
    import json
    cache_key = hashlib.md5(json.dumps(symbol_map, sort_keys=True).encode()).hexdigest()
    cache_file = f".cache/prices/{cache_key}.pkl"

    # Try to load from disk cache if fresh
    if os.path.exists(cache_file) and (time.time() - os.path.getmtime(cache_file) < CACHE_TTL_SEC):
        with open(cache_file, "rb") as f:
            prices, errors = pickle.load(f)
        last_updated = datetime.fromtimestamp(os.path.getmtime(cache_file))
        return prices, errors, last_updated

    prices = {}
    errors = []

    with st.spinner("🔄 Fetching real-time market data..."):
        progress_bar = st.progress(0)
        total = len(symbol_map)

        for idx, (name, ticker) in enumerate(symbol_map.items()):
            try:
                if "10y" in name.lower() or "2y" in name.lower() or "30y" in name.lower():
                    # Use FRED for bond yields
                    if name == "us10y_quote":
                        series = fred.get_series("DGS10")
                    elif name == "us2y_quote":
                        series = fred.get_series("DGS2")
                    elif name == "us30y_quote":
                        series = fred.get_series("DGS30")
                    elif name == "de10y_quote":
                        series = fred.get_series("IRLTLT01DEM156N")
                    elif name == "uk10y_quote":
                        series = fred.get_series("IRLTLT01GBM156N")
                    else:
                        continue

                    if series is not None and len(series) > 0:
                        current = float(series.dropna().iloc[-1])
                        prev = float(series.dropna().iloc[-2]) if len(series.dropna()) > 1 else current
                        prices[name] = {
                            "current": round(current, 3),
                            "change": round(current - prev, 3),
                            "pct_change": round((current - prev) / prev * 100, 2) if prev != 0 else 0,
                            "timestamp": datetime.now()
                        }
                else:
                    # Use yfinance for everything else
                    ticker_obj = yf.Ticker(ticker)
                    info = ticker_obj.info
                    hist = ticker_obj.history(period="2d")

                    if len(hist) >= 1:
                        current = hist['Close'].iloc[-1]
                        prev = hist['Close'].iloc[-2] if len(hist) >= 2 else current

                        prices[name] = {
                            "current": round(current, 4),
                            "change": round(current - prev, 4),
                            "pct_change": round((current - prev) / prev * 100, 2) if prev != 0 else 0,
                            "timestamp": datetime.now(),
                            "volume": hist['Volume'].iloc[-1] if 'Volume' in hist else None
                        }

            except Exception as e:
                prices[name] = {"current": "N/A", "error": str(e)}
                errors.append(f"{name}: {str(e)}")

            progress_bar.progress((idx + 1) / total)

        progress_bar.empty()

    # Save to disk cache
    with open(cache_file, "wb") as f:
        pickle.dump((prices, errors), f)
    last_updated = datetime.now()
    return prices, errors, last_updated



@st.cache_data
def get_comprehensive_news(assets_focus=None):
    """Aggregate news from multiple sources with smart filtering"""
    all_news = {}

    # Define search keywords for each asset class
    search_terms = {
        "fx": ["dollar", "forex", "currency", "DXY", "EUR/USD", "GBP/USD", "central bank"],
        "commodities": ["gold", "oil", "crude", "WTI", "precious metals", "copper", "commodity"],
        "rates": ["bond", "yield", "treasury", "interest rate", "Fed", "ECB", "BOE", "BOJ"],
        "equities": ["stock", "S&P", "NASDAQ", "equity", "earnings", "market"],
        "macro": ["inflation", "CPI", "GDP", "unemployment", "PMI", "retail sales", "FOMC"]
    }

    try:
        # Finnhub news
        finnhub_key = st.secrets.get("finnhub_api_key", "d07lgo1r01qrslhp3q3g")
        for category in ["general", "forex", "crypto"]:
            url = f"https://finnhub.io/api/v1/news?category={category}&token={finnhub_key}"
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                articles = response.json()
                for article in articles[:20]:  # Limit to recent articles
                    # Smart categorization
                    headline = article.get("headline", "").lower()
                    summary = article.get("summary", "").lower()
                    content = headline + " " + summary

                    categories = []
                    for cat, keywords in search_terms.items():
                        if any(kw.lower() in content for kw in keywords):
                            categories.append(cat)

                    if categories:
                        for cat in categories:
                            if cat not in all_news:
                                all_news[cat] = []
                            all_news[cat].append({
                                "headline": article.get("headline"),
                                "summary": article.get("summary"),
                                "url": article.get("url"),
                                "datetime": datetime.fromtimestamp(article.get("datetime", 0)),
                                "source": "Finnhub"
                            })

        # NewsAPI
        newsapi_key = st.secrets.get("newsapi_key", "713b3bd82121482aaa0ecdc9af77b6da")
        for query in ["forex", "commodity", "federal reserve", "ECB", "inflation"]:
            url = f"https://newsapi.org/v2/everything?q={query}&language=en&sortBy=publishedAt&apiKey={newsapi_key}"
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                for article in data.get("articles", [])[:10]:
                    # Categorize
                    title = article.get("title", "").lower()
                    desc = article.get("description", "").lower()
                    content = title + " " + desc

                    categories = []
                    for cat, keywords in search_terms.items():
                        if any(kw.lower() in content for kw in keywords):
                            categories.append(cat)

                    if categories:
                        for cat in categories:
                            if cat not in all_news:
                                all_news[cat] = []
                            all_news[cat].append({
                                "headline": article.get("title"),
                                "summary": article.get("description"),
                                "url": article.get("url"),
                                "datetime": datetime.fromisoformat(article.get("publishedAt", "").replace("Z", "")),
                                "source": "NewsAPI"
                            })

    except Exception as e:
        st.error(f"News aggregation error: {str(e)}")

    # Sort by datetime and remove duplicates
    for category in all_news:
        # Remove duplicates based on headline
        seen = set()
        unique_news = []
        for article in sorted(all_news[category], key=lambda x: x["datetime"], reverse=True):
            if article["headline"] not in seen:
                seen.add(article["headline"])
                unique_news.append(article)
        all_news[category] = unique_news[:15]  # Keep top 15 per category

    return all_news

@st.cache_data(ttl=86400)  # Cache for 1 day
def generate_professional_macro_analysis(snapshot, news_data, econ_events):
    """Generate Bloomberg-style macro analysis"""

    # Prepare the summary table
    summary_table_rows = []
    instruments = [
        ("DXY", "dxy_quote", False),
        ("EUR/USD", "eurusd_quote", False),
        ("GBP/USD", "gbpusd_quote", False),
        ("EUR/GBP", "eurgbp_quote", False),
        ("USD/JPY", "usdjpy_quote", False),
        ("Gold", "gold_quote", False),
        ("WTI Oil", "oil_quote", False),
        ("US 10Y", "us10y_quote", True),
        ("UK 10Y", "uk10y_quote", True),
        ("DE 10Y", "de10y_quote", True),
        ("S&P 500", "spx_quote", False),
        ("VIX", "vix_quote", False),
    ]

    for display, key, is_yield in instruments:
        if key in snapshot:
            data = snapshot[key]
            if isinstance(data, dict):
                price = data.get("current", "N/A")
                change = data.get("change", 0)
                pct = data.get("pct_change", 0)

                if price != "N/A":
                    if is_yield:
                        price_str = f"{price:.3f}%"
                        change_str = f"{change:+.3f}bps"
                    else:
                        if "USD" in display or "GBP" in display or "EUR" in display:
                            price_str = f"{price:.5f}"
                            change_str = f"{change:+.5f}"
                        else:
                            price_str = f"{price:.2f}"
                            change_str = f"{change:+.2f}"

                    trend = "↑" if change > 0 else "↓" if change < 0 else "→"

                    # Determine sentiment
                    if abs(pct) > 1:
                        sentiment = "Bullish" if change > 0 else "Bearish"
                    else:
                        sentiment = "Neutral"

                    # Get relevant news context
                    news_context = "Monitoring market flows"
                    if "fx" in news_data and news_data["fx"]:
                        for article in news_data["fx"][:3]:
                            if display.lower().replace("/", "") in article["headline"].lower():
                                news_context = article["headline"][:60] + "..."
                                break

                    summary_table_rows.append(
                        f"| {display} | {price_str} | {change_str} ({pct:+.1f}%) | "
                        f"{trend} {sentiment} | {news_context} |"
                    )

    # Format the complete prompt
    summary_table = "\\n".join(summary_table_rows)

    # Prepare economic events summary
    events_summary = ""
    if not econ_events.empty:
        top_events = econ_events.head(5)
        events_list = []
        for _, event in top_events.iterrows():
            events_list.append(
                f"• {event['country']}: {event['event']} "
                f"(Forecast: {event.get('forecast', 'N/A')}, Previous: {event.get('previous', 'N/A')})"
            )
        events_summary = "\\n".join(events_list)

    prompt = f"""You are a senior macro strategist at a top-tier investment bank writing the morning note for institutional clients.

## 📊 Macro Sentiment Summary – {datetime.now().strftime('%Y-%m-%d %H:%M')} UTC

### 🧾 Key Cross-Asset Dashboard

| Instrument | Current Price | Change | Trend | Key Macro Context |
|----|----|----|----|----|
{summary_table}

### 📅 Today's Key Economic Releases
{events_summary if events_summary else "No high-impact releases scheduled"}

Write a concise but comprehensive macro analysis following this structure:

1. **🔍 Market Movers & Macro Drivers** 
   - FX: Focus on DXY, EUR, GBP, JPY flows and central bank expectations
   - Rates: Yield curve dynamics and monetary policy implications  
   - Commodities: Energy and precious metals with geopolitical context
   - Risk: VIX and cross-asset volatility regime

2. **🧠 Key Themes Driving Markets**
   - Identify 3 main macro themes
   - Connect price action to fundamental drivers
   - Highlight any divergences or regime changes

3. **⚡ Trade Ideas & Risk Scenarios**
   - 2-3 actionable trade ideas with clear rationale
   - Key risk events and levels to watch
   - Correlation breaks or unusual flows

Use professional language, cite specific levels, and focus on what matters for trading today.
Be direct, quantitative, and actionable. No generic statements."""

    try:
        response = client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=2000
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Analysis generation error: {str(e)}"

@st.cache_data
def get_economic_calendar():
    """Fetch comprehensive economic calendar"""
    try:
        # Trading Economics API
        api_key = st.secrets.get("trading_economics_api_key", "1750867cdfc34c6:288nxdz64y932qq")
        countries = ["united states", "euro area", "united kingdom", "japan", "china", "germany"]

        all_events = []
        for country in countries:
            url = f"https://api.tradingeconomics.com/calendar/country/{country}?c={api_key}"
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                events = response.json()
                all_events.extend(events)

        # Convert to DataFrame
        if all_events:
            df = pd.DataFrame(all_events)
            df['date'] = pd.to_datetime(df['date'])

            # Filter for next 7 days
            today = pd.Timestamp.now()
            week_ahead = today + pd.Timedelta(days=7)
            df = df[(df['date'] >= today) & (df['date'] <= week_ahead)]

            # Sort by importance and date
            importance_map = {"Low": 1, "Medium": 2, "High": 3}
            df['importance_num'] = df['importance'].map(importance_map).fillna(1)
            df = df.sort_values(['date', 'importance_num'], ascending=[True, False])

            return df[['date', 'country', 'event', 'actual', 'forecast', 'previous', 'importance']]

    except Exception as e:
        st.error(f"Calendar fetch error: {str(e)}")

    return pd.DataFrame()

@st.cache_data
def calculate_technical_indicators(ticker, period="1mo"):
    """Calculate professional technical indicators"""
    try:
        data = yf.download(ticker, period=period, interval="1h")
        if data.empty:
            return None

        # Calculate indicators
        data['SMA_20'] = data['Close'].rolling(20).mean()
        data['SMA_50'] = data['Close'].rolling(50).mean()
        data['EMA_12'] = data['Close'].ewm(span=12).mean()
        data['EMA_26'] = data['Close'].ewm(span=26).mean()
        data['MACD'] = data['EMA_12'] - data['EMA_26']
        data['Signal'] = data['MACD'].ewm(span=9).mean()

        # RSI
        delta = data['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        data['RSI'] = 100 - (100 / (1 + rs))

        # Bollinger Bands
        data['BB_middle'] = data['Close'].rolling(20).mean()
        bb_std = data['Close'].rolling(20).std()
        data['BB_upper'] = data['BB_middle'] + 2 * bb_std
        data['BB_lower'] = data['BB_middle'] - 2 * bb_std

        # Support/Resistance
        data['Pivot'] = (data['High'] + data['Low'] + data['Close']) / 3
        data['R1'] = 2 * data['Pivot'] - data['Low']
        data['S1'] = 2 * data['Pivot'] - data['High']
        data['R2'] = data['Pivot'] + (data['High'] - data['Low'])
        data['S2'] = data['Pivot'] - (data['High'] - data['Low'])

        return data

    except Exception as e:
        return None

def compute_rsi(values, period=14):
    """Simple RSI computation"""
    deltas = np.diff(values)
    seed = deltas[:period+1]
    up = seed[seed >= 0].sum()/period
    down = -seed[seed < 0].sum()/period
    rs = up/down if down != 0 else 0
    rsi = np.zeros_like(values)
    rsi[:period] = 100.
    for i in range(period, len(values)):
        delta = deltas[i-1]
        if delta > 0:
            upval = delta
            downval = 0.
        else:
            upval = 0.
            downval = -delta
        up = (up*(period-1) + upval)/period
        down = (down*(period-1) + downval)/period
        rs = up/down if down != 0 else 0
        rsi[i] = 100. - 100./(1. + rs)
    return rsi

def render_market_card_pro(asset_key, prices, peer_moves, news_dict, rsi_dict=None, vol_dict=None, is_top_mover=False):
    import plotly.graph_objects as go
    label = ENHANCED_DISPLAY_NAMES.get(asset_key, asset_key)
    data = prices.get(asset_key, {})
    try:
        hist = yf.Ticker(PROFESSIONAL_SYMBOL_MAP[asset_key]).history(period="1mo")['Close']
        values = hist.dropna().values[-20:] if len(hist) >= 20 else hist.dropna().values
        asset_high = hist.dropna().max()
        asset_low = hist.dropna().min()
    except Exception:
        values = []
        asset_high = asset_low = None

    value = data.get("current", "N/A")
    delta = data.get("change", 0)
    pct = data.get("pct_change", 0)

    # Volatility
    vol = None
    if len(values) > 1:
        vol = np.std(np.diff(values)) * np.sqrt(252) / np.mean(values) * 100
        vol = f"{vol:.1f}"

    # RSI
    rsi = None
    if len(values) >= 15:
        rsi = compute_rsi(values)[-1]
        rsi = int(rsi)
    signal = "Neutral"
    sig_color = "#bdbdbd"
    if rsi:
        if rsi > 70:
            signal, sig_color = "Overbought", "#e57373"
        elif rsi < 30:
            signal, sig_color = "Oversold", "#64b5f6"
        else:
            signal = "Neutral"

    # PATCH: Hide Range if N/A
    if asset_low is not None and asset_high is not None and not (np.isnan(asset_low) or np.isnan(asset_high)):
        range_str = f"Range: {asset_low:.2f}–{asset_high:.2f}"
    else:
        range_str = ""

    # PATCH: Improved Mini-News Relevance
    mini_news = ""
    # Search for relevant news: prefer rates/macro, then fx
    for cat in ['rates', 'macro', 'fx']:
        for article in news_dict.get(cat, []):
            if ENHANCED_DISPLAY_NAMES.get(asset_key, asset_key).split()[0].lower() in article.get("headline", "").lower():
                mini_news = article.get("headline", "")
                break
        if mini_news:
            break
    # fallback to top general news if nothing found
    if not mini_news:
        mini_news = news_dict.get(asset_key, [""])[0]

    mover_badge = '<span style="background:#ff9800;color:#fff;font-size:0.88em;padding:1px 7px;border-radius:7px;margin-right:6px;">🔥 Top Mover</span>' if is_top_mover else ""

    fig = go.Figure()
    if len(values) > 1:
        fig.add_trace(go.Scatter(
            y=values, mode="lines", line=dict(color="gold", width=2), showlegend=False
        ))
    fig.update_layout(
        height=52,
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
    )

    # Format value
    value_str = f"{value:.2f}" if isinstance(value, (float, int)) else str(value)
    delta_str = f"{delta:+.2f}"
    delta_color = "green" if delta >= 0 else "red"

    # PATCH: Only show range span if range_str is not empty
    range_html = f'<span style="font-size:0.98em;color:#bdbdbd;">{range_str}</span>' if range_str else ""

    st.markdown(
        f"""
        <div style="text-align:center;margin-bottom:10px;padding:10px 0 0 0;">
            <div style="font-size:1.3em;font-weight:800;color:#ffe082;">{label} {mover_badge}</div>
            <div style="font-size:2.5em;font-weight:700;color:#fff;">{value_str}</div>
            <div style="font-size:1.1em;font-weight:500;color:{delta_color};margin-bottom:2px;">
                {delta_str} ({pct:+.2f}%)
            </div>
            {f'<div style="margin:2px 0 3px 0;font-size:0.98em;">{range_html}<span style="background:{sig_color};color:#181818;padding:2px 8px 2px 8px;border-radius:8px;">{signal}</span>{" | 1w Vol: " + str(vol) + "%" if vol else ""}{" | RSI: " + str(rsi) if rsi else ""}</div>' if (range_html or sig_color or vol or rsi) else ""}
            <div style="margin-top:3px;min-height:1.5em;font-size:0.99em;color:#90caf9;">
                {mini_news}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

# Main dashboard
def main():
    # Ensure session state keys are initialized
    if 'data' not in st.session_state:
        st.session_state['data'] = {}
    if 'ai_trading_ideas' not in st.session_state['data']:
        st.session_state['data']['ai_trading_ideas'] = []
    if 'news' not in st.session_state['data']:
        st.session_state['data']['news'] = []
    st.markdown("""
    <div style='text-align:center; margin-bottom: 0.6em;'>
        <span style='font-size:2.45em; font-weight:700; color:#ffe082; letter-spacing:1.1px; font-family: "Segoe UI", "Roboto", Arial, sans-serif;'>
            Macro Intelligence Dashboard
        </span><br>
        <span style='font-size:1.13em; color:#d8dee9; font-weight:400; letter-spacing:0.6px; font-family: "Segoe UI", "Roboto", Arial, sans-serif;'>
            Real-Time Institutional-Grade Market Analytics
        </span>
    </div>
    <div style='text-align:right; color:#bbb; font-size:0.98em; margin-bottom:0.7em;'>
        Last Update: """ + datetime.now().strftime('%Y-%m-%d %H:%M UTC') + """ 
    </div>
    """, unsafe_allow_html=True)

    # (CSS handled globally above)
    # --- Institutional Macro CSS block ---
    st.markdown("""
    <style>
        .macro-events-pro {
            background: linear-gradient(92deg,rgba(36,36,60,0.07) 70%,rgba(36,46,80,0.07));
            border-radius: 17px;
            border: 1.5px solid #32333f;
            box-shadow: 0 4px 18px 2px rgba(34,32,62,0.27);
            padding: 26px 30px 19px 30px;
            margin-bottom: 23px;
        }
        .macro-events-pro h2 {
            font-size: 2.1em;
            font-weight: 800;
            color: #ffe082;
            margin: 0 0 0.5em 0;
            letter-spacing: 1.3px;
            text-shadow: 0 1px 12px #3337;
        }
        .macro-events-pro hr {
            margin: 0.7em 0 1.3em 0;
            border: none;
            border-top: 1.2px solid #7b7a85;
        }
        .macro-dot {
            color: #ffeb3b;
            font-size: 1.2em;
            vertical-align: middle;
            margin-right: 6px;
        }
        .macro-events-pro ul {
            margin: 0.2em 0 1.1em 0;
            padding-left: 1.3em;
        }
        .macro-events-pro li {
            margin-bottom: 0.45em;
            font-size: 1.14em;
        }
        .macro-impact-pro {
            background: linear-gradient(95deg,rgba(30,35,50,0.10) 65%,rgba(20,20,30,0.10));
            border-radius: 14px;
            border: 1px solid #39384a;
            box-shadow: 0 2px 14px 1px rgba(54, 54, 84, 0.13);
            padding: 18px 23px 12px 23px;
            margin-bottom: 25px;
        }
        .macro-impact-pro b {
            color: #99ffd0;
            font-size: 1.1em;
        }
        .macro-impact-pro hr {
            margin: 0.8em 0 0.7em 0;
            border: none;
            border-top: 1.1px solid #434356;
        }
        /* --- PATCH: Market Card Pro Grid Styling --- */
        .pro-micro-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 24px 30px;
            margin-bottom: 32px;
        }
        @media (max-width: 1100px) {
            .pro-micro-grid { grid-template-columns: 1fr 1fr; }
        }
        @media (max-width: 750px) {
            .pro-micro-grid { grid-template-columns: 1fr; }
        }
        .pro-micro-cell {
            background: rgba(28, 28, 32, 0.91);
            border-radius: 14px;
            border: 1.4px solid rgba(255,255,255,0.09);
            box-shadow: 0 2px 14px 0 rgba(0,0,0,0.23);
            padding: 16px 10px 12px 10px;
            min-width: 0;
        }
    </style>
    """, unsafe_allow_html=True)

    # --- PATCH: 3x3 Market Grid (DXY, VIX, Gold, Oil, US 10Y, DE 10Y, NASDAQ, S&P, DAX) ---
    # This block is inserted right before the large heading “ANALYSIS”.
    # Asset order: [DXY, VIX, Gold], [Oil, US 10Y, DE 10Y], [NASDAQ, S&P, DAX]
    grid_assets = [
        ["dxy_quote", "vix_quote", "gold_quote"],
        ["oil_quote", "us10y_quote", "de10y_quote"],
        ["nasdaq_quote", "spx_quote", "dax_quote"]
    ]
    flat_assets = [item for sublist in grid_assets for item in sublist]
    chart_assets = flat_assets
    # Fetch prices for these assets
    prices_grid, price_errors_grid, last_update_grid = get_validated_prices({k: PROFESSIONAL_SYMBOL_MAP[k] for k in flat_assets})
    last_update_ts = last_update_grid
    # Prepare news headlines per asset for context line
    all_news_grid = get_comprehensive_news()
    news_dict_grid = {}
    for asset in flat_assets:
        news_dict_grid[asset] = []
        for cat in all_news_grid:
            for article in all_news_grid[cat]:
                headline = article.get("headline", "")
                if ENHANCED_DISPLAY_NAMES.get(asset, asset).split()[0].lower() in headline.lower():
                    news_dict_grid[asset].append(headline)
        if not news_dict_grid[asset]:
            news_dict_grid[asset] = [all_news_grid['fx'][0]['headline']] if 'fx' in all_news_grid and all_news_grid['fx'] else [""]
    # Find top % mover in this grid
    pct_moves_grid = [(asset, abs(prices_grid.get(asset, {}).get("pct_change", 0))) for asset in flat_assets]
    top_mover_grid = max(pct_moves_grid, key=lambda x: x[1])[0] if pct_moves_grid else None
    # Render the grid using HTML/CSS for exact 3x3 layout (as in MyMicroSentiment)
    st.markdown("<div class='pro-micro-grid'>", unsafe_allow_html=True)
    for row in grid_assets:
        for asset in row:
            st.markdown("<div class='pro-micro-cell'>", unsafe_allow_html=True)
            render_market_card_pro(
                asset, prices_grid, None, news_dict_grid,
                rsi_dict=None, vol_dict=None,
                is_top_mover=(asset == top_mover_grid)
            )
            st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    # --- Events & Macro Drivers summary block ---
    st.markdown("""
    <div class="macro-events-pro">
        <h2>📅 Events & Macro Drivers</h2>
        <hr>
        <b>Today / Upcoming:</b>
        <ul>
            <li><span class="macro-dot">●</span><b>Fri 13:30 UTC</b> – US Non-Farm Payrolls <span style="color:#aaa;">(USD pairs, S&P, Bonds)</span></li>
            <li><span class="macro-dot">●</span><b>Wed 12:30 UTC</b> – US CPI <span style="color:#aaa;">(USD pairs, Gold, S&P, NASDAQ)</span></li>
            <li><span class="macro-dot">●</span><b>Thu 18:00 UTC</b> – FOMC Minutes <span style="color:#aaa;">(risk, rates, DXY, Gold)</span></li>
        </ul>
        <b>Central Bank Watch:</b>
        <ul>
            <li><span class="macro-dot" style="color:#90caf9;">●</span>ECB President Lagarde speaks 09:00 UTC <span style="color:#aaa;">(EUR, DAX)</span></li>
            <li><span class="macro-dot" style="color:#b2ff59;">●</span>Fed's Powell speaks this afternoon <span style="color:#aaa;">(USD, S&P, Treasuries)</span></li>
        </ul>
    </div>
    """, unsafe_allow_html=True)


    # --- This Week's Key Event Watchlist (inserted block) ---
    st.markdown("""
<div class="macro-impact-pro" style="margin-bottom:18px;">
  <span style="font-size:1.2em;font-weight:700;color:#ffe082;">🔍 This Week's Key Event Watchlist</span>
  <ul style="margin-top:0.7em; margin-bottom:0.7em;">
    <li><b>EUR:</b> ECB President Lagarde speaks (Fri 09:00 UTC), Germany Factory Orders (Thu), Eurozone Retail Sales (Wed)</li>
    <li><b>GBP:</b> UK GDP (Fri), BOE’s Mann speaks (Wed), UK Services PMI Final (Tue)</li>
    <li><b>Gold/Oil:</b> US Non-Farm Payrolls (Fri), US CPI (Wed), EIA Oil Inventories (Thu), OPEC Monthly Report (Thu)</li>
  </ul>
  <span style="font-size:0.99em; color:#bdbdbd;">* Watch these for likely volatility in EUR/USD, GBP/USD, Gold (XAU/USD), and Oil (WTI).</span>
</div>
""", unsafe_allow_html=True)

    # --- Dynamic news impact summary using recent FX news ---
    # News impact summary (top headlines and expected market impact)
    all_news = get_comprehensive_news()
    top_news = []
    if 'fx' in all_news and all_news['fx']:
        top_news = all_news['fx'][:3]

    news_lines = []
    for article in top_news:
        headline = article["headline"]
        impact_asset = ""
        if "usd" in headline.lower(): impact_asset = "USD pairs"
        elif "eur" in headline.lower(): impact_asset = "EUR/USD, EUR crosses"
        elif "gbp" in headline.lower(): impact_asset = "GBP/USD, FTSE"
        elif "jpy" in headline.lower(): impact_asset = "USD/JPY, Nikkei"
        elif "cpi" in headline.lower(): impact_asset = "Inflation trades, Bonds, Gold"
        elif "fed" in headline.lower() or "powell" in headline.lower(): impact_asset = "Rates, USD, S&P"
        else: impact_asset = "Macro assets"
        news_lines.append(
            f"""<b>{headline}</b>
            <br><span style='color:#9fffe0;'>Impacts:</span> {impact_asset}
            <br><span style='color:#f4b400;'>Potential:</span> Expect movement if referenced during next major release.
            <br><span style='font-size:0.96em; color:#ffd700;'>({article['datetime'].strftime('%Y-%m-%d %H:%M')})</span>
            <hr>"""
        )

    if news_lines:
        st.markdown(
            '<div class="macro-impact-pro">'
            '<b>📰 Recent Headlines & Expected Impact:</b><br>'
            + "".join(news_lines)
            + '</div>',
            unsafe_allow_html=True,
        )

    # --- Refresh Button at Top ---
    refresh_button = st.button("🔄 Refresh Quotes", key="refresh_quotes", use_container_width=True)
    if refresh_button:
        st.cache_data.clear()

    # --- ANALYSIS section below the grid ---
    st.markdown(
        "<div style='text-align:center; font-size:2em; font-weight:bold; color:#fff; margin-top:30px; margin-bottom:20px;'>ANALYSIS</div>",
        unsafe_allow_html=True
    )
    # Macro analysis using professional function, inside market-card
    # Only pass the snapshot of the nine assets
    prices = prices_grid
    filtered_prices = {k: prices[k] for k in chart_assets if k in prices}

    # Add refresh button for macro analysis
    if st.button("🔁 Refresh Analysis", key="refresh_analysis", use_container_width=True):
        st.cache_data.clear()

    import hashlib
    import json
    prices_key = hashlib.md5(json.dumps(filtered_prices, sort_keys=True, default=str).encode()).hexdigest()
    # Dummy news and econ_events for analysis function (empty as per instructions)
    with st.spinner("🧠 Generating Macro Intelligence..."):
        analysis = generate_professional_macro_analysis(filtered_prices, {}, pd.DataFrame())
    st.markdown('<div class="market-card">', unsafe_allow_html=True)
    st.markdown(analysis)
    st.markdown('</div>', unsafe_allow_html=True)

    # --- Enhanced Macro Insight Block ---
    # Show the true last update timestamp for prices
    last_update_str = last_update_ts.strftime('%Y-%m-%d %H:%M UTC') if last_update_ts else datetime.now().strftime('%Y-%m-%d %H:%M UTC')
    st.markdown(
        f"""
        <div style='margin-top: 20px; margin-bottom: 10px; padding: 16px 18px 8px 18px; background: rgba(20,20,25,0.80); border-radius: 10px; color: #f1f1f1;'>
        <b>🗓️ Upcoming Economic Releases</b><br>
        <span style='font-size:1.04em'>
        • <b>Fri 13:30 UTC</b> – US Non-Farm Payrolls<br>
        • <b>Wed 12:30 UTC</b> – US CPI<br>
        • <b>Thu 18:00 UTC</b> – FOMC Minutes<br>
        </span>
        <hr style='margin:10px 0 10px 0; border-top: 1px solid #555;'>
        <b>🏦 Central Bank Watch</b><br>
        <span style='font-size:1.03em'>
        • ECB President Lagarde speaks 09:00 UTC<br>
        • Fed's Powell (tentative) this afternoon<br>
        </span>
        <hr style='margin:10px 0 10px 0; border-top: 1px solid #555;'>
        <b>💼 Positioning & Flows</b><br>
        <span style='font-size:1.01em'>
        • CFTC shows net USD longs remain near YTD highs.<br>
        • Leveraged funds add to NASDAQ and Gold exposure.<br>
        </span>
        <hr style='margin:10px 0 10px 0; border-top: 1px solid #555;'>
        <b>⚡ Implied Volatility (snapshot)</b><br>
        <span style='font-size:1.01em'>
        • VIX: 16.4 (1m avg 15.9), EUR/USD 1w vol: 5.4%, Gold vol subdued.<br>
        </span>
        <hr style='margin:10px 0 10px 0; border-top: 1px solid #555;'>
        <b>🔑 Key Levels to Watch</b><br>
        <span style='font-size:1.01em'>
        • S&P 500: 6300 (pivot), 6220 (support)<br>
        • EUR/USD: 1.0850, 1.0920 (range)<br>
        • US 10Y: 4.33% (yield breakout)<br>
        </span>
        <hr style='margin:10px 0 10px 0; border-top: 1px solid #555;'>
        <span style='font-size:0.98em; color:#bdbdbd;'>Last Update: {last_update_str}</span>
        </div>
        """,
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()