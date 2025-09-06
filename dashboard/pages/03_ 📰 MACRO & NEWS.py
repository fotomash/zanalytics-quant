
import pickle
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import requests
import glob
import os
from pathlib import Path
from datetime import datetime, timedelta
from datetime import timezone
import warnings
import re
from typing import Dict, List, Optional, Tuple, Any, Union
from bs4 import BeautifulSoup
import base64
import yfinance as yf
from fredapi import Fred
import streamlit as st
from openai import OpenAI
import hashlib
import json
import time

# Suppress warnings
warnings.filterwarnings('ignore')

st.set_page_config(
    page_title="Elite Trading Desk Pro",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- IMAGE BACKGROUND & STYLING (from Home.py) ---
def get_image_as_base64(path):
    """Reads an image file and returns its base64 encoded string."""
    try:
        with open(path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode()
    except FileNotFoundError:
        st.warning(f"Background image not found at '{path}'. Please ensure it's in the same directory as the script.")
        return None

img_base64 = get_image_as_base64("image_af247b.jpg")
if img_base64:
    background_style = f"""
    <style>
    [data-testid="stAppViewContainer"] > .main {{
        background-image: linear-gradient(rgba(0,0,0,0.8), rgba(0,0,0,0.8)), url(data:image/jpeg;base64,{img_base64});
        background-size: cover;
        background-position: center;
        background-repeat: no-repeat;
        background-attachment: fixed;
    }}
    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    </style>
    """
    st.markdown(background_style, unsafe_allow_html=True)

st.markdown("""
<style>
.main .block-container {
    background-color: rgba(0,0,0,0.025) !important;
}
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'cached_data' not in st.session_state:
    st.session_state['cached_data'] = {}
if 'last_refresh' not in st.session_state:
    st.session_state['last_refresh'] = None
if 'auto_refresh_enabled' not in st.session_state:
    st.session_state['auto_refresh_enabled'] = False

# Cache configuration
CACHE_DIR = ".cache"
CACHE_EXPIRY_MINUTES = 15

def ensure_cache_dir():
    """Ensure cache directory exists"""
    os.makedirs(CACHE_DIR, exist_ok=True)

ensure_cache_dir()

# Initialize OpenAI client
# --- OpenAI key bootstrap (safe) -------------------------------------------
import os

# Support both naming conventions for OpenAI API key
api_key = st.secrets.get("OPENAI_API_KEY") or st.secrets.get("openai_API")
if api_key:
    try:
        client = OpenAI(api_key=api_key)
        st.sidebar.success("✅ OpenAI key loaded")
    except Exception as e:
        st.sidebar.warning(f"⚠️ Failed to init OpenAI client: {e}")
        client = None
else:
    st.sidebar.warning("⚠️ OPENAI_API_KEY not found – OpenAI features disabled.")
    client = None
# ---------------------------------------------------------------------------

# --- VISUAL STYLING ---
# Remove or comment out any previous or conflicting image background code that sets `.stApp`'s background or image.
def apply_advanced_styling():
    """Apply comprehensive visual styling"""
    return """
    <style>
    /* Base theme */
    /* .stApp {
        background: linear-gradient(135deg, #0a0e27 0%, #151932 100%);
        color: #ffffff;
    } */
    /* Enhanced metrics */
    [data-testid="metric-container"] {
        background: linear-gradient(135deg, rgba(59, 130, 246, 0.1), rgba(139, 92, 246, 0.1));
        border: 1px solid rgba(59, 130, 246, 0.3);
        border-radius: 12px;
        padding: 1rem;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
        transition: all 0.3s ease;
    }
    [data-testid="metric-container"]:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(59, 130, 246, 0.3);
        border-color: rgba(59, 130, 246, 0.5);
    }
    /* News items */
    .news-item {
        background: rgba(26, 29, 58, 0.6);
        padding: 1rem;
        border-radius: 10px;
        margin: 0.5rem 0;
        border-left: 4px solid #3b82f6;
        transition: all 0.3s ease;
    }
    .news-item:hover {
        background: rgba(26, 29, 58, 0.8);
        transform: translateX(5px);
    }
    .high-impact {
        border-left-color: #ef4444;
        background: rgba(239, 68, 68, 0.1);
    }
    .medium-impact {
        border-left-color: #f59e0b;
        background: rgba(245, 158, 11, 0.1);
    }
    .low-impact {
        border-left-color: #10b981;
        background: rgba(16, 185, 129, 0.1);
    }
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        background: rgba(26, 29, 58, 0.5);
        border-radius: 10px;
        padding: 0.5rem;
        gap: 0.5rem;
    }
    .stTabs [data-baseweb="tab"] {
        background: transparent;
        color: #94a3b8;
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #3b82f6, #8b5cf6);
        color: white;
    }
    /* Buttons */
    .stButton > button {
        background: linear-gradient(135deg, #3b82f6, #8b5cf6);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.5rem 2rem;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 5px 20px rgba(59, 130, 246, 0.4);
    }
    /* Cards */
    .dashboard-card {
        background: rgba(26, 29, 58, 0.4);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 15px;
        padding: 1.5rem;
        margin: 1rem 0;
    }
    /* Expanders */
    .streamlit-expanderHeader {
        background: rgba(59, 130, 246, 0.1);
        border-radius: 8px;
    }
    /* Dataframes */
    .dataframe {
        background: rgba(26, 29, 58, 0.6);
        border-radius: 10px;
    }
    </style>
    """

# --- SECTION STYLING STUB ---
def apply_section_styling(section):
    # Placeholder for section-specific CSS (currently returns nothing)
    return ""

# --- ENHANCED PRICE PIPELINE ---
def get_prices(symbol_map):
    """Get prices with enhanced error handling and caching"""
    prices = {}
    for name, ticker in symbol_map.items():
        try:
            ticker_obj = yf.Ticker(ticker)
            hist = ticker_obj.history(period="2d")

            if not hist.empty and len(hist) >= 2:
                current = float(hist['Close'].iloc[-1])
                previous = float(hist['Close'].iloc[-2])
                change = current - previous
                pct_change = (change / previous) * 100 if previous != 0 else 0

                prices[name] = {
                    "current": round(current, 4),
                    "change": round(change, 4),
                    "percentChange": round(pct_change, 2),
                    "timestamp": datetime.now().isoformat()
                }
            else:
                data = ticker_obj.info
                last_price = data.get("regularMarketPrice", data.get("previousClose"))
                if last_price:
                    prices[name] = {
                        "current": round(last_price, 4),
                        "change": 0,
                        "percentChange": 0,
                        "timestamp": datetime.now().isoformat()
                    }
                else:
                    prices[name] = {"current": "N/A", "error": "No data available"}
        except Exception as e:
            prices[name] = {"current": "N/A", "error": str(e)}

    return prices

# --- CACHING SYSTEM ---
class CacheManager:
    @staticmethod
    def get_cache_path(key):
        return os.path.join(CACHE_DIR, f"{key}.pkl")

    @staticmethod
    def is_cache_valid(key, expiry_minutes=CACHE_EXPIRY_MINUTES):
        cache_path = CacheManager.get_cache_path(key)
        if not os.path.exists(cache_path):
            return False
        file_age = datetime.now() - datetime.fromtimestamp(os.path.getmtime(cache_path))
        return file_age.total_seconds() < (expiry_minutes * 60)

    @staticmethod
    def save_cache(data, key):
        cache_path = CacheManager.get_cache_path(key)
        with open(cache_path, "wb") as f:
            pickle.dump({
                'data': data,
                'timestamp': datetime.now()
            }, f)

    @staticmethod
    def load_cache(key):
        cache_path = CacheManager.get_cache_path(key)
        try:
            with open(cache_path, "rb") as f:
                cache_data = pickle.load(f)
                return cache_data['data']
        except:
            return None

    @staticmethod
    def clear_cache(pattern="*"):
        import glob
        cache_files = glob.glob(os.path.join(CACHE_DIR, f"{pattern}.pkl"))
        for f in cache_files:
            try:
                os.remove(f)
            except:
                pass

# --- COMPREHENSIVE NEWS SCANNER ---
class ComprehensiveNewsScanner:
    def __init__(self):
        self.cache_manager = CacheManager()

        # Extended keyword mapping including all requested pairs
        self.asset_keywords = {
            'DXY': ['DXY', 'Dollar Index', 'USD', 'Dollar', 'USDX', 'Buck', 'Greenback'],
            'VIX': ['VIX', 'Volatility', 'Fear Index', 'CBOE', 'Vol', 'Market Fear'],
            'Gold': ['Gold', 'XAU', 'XAUUSD', 'Precious Metals', 'Safe Haven', 'Bullion'],
            'Oil': ['Oil', 'WTI', 'Crude', 'Brent', 'Energy', 'OPEC', 'Petroleum'],
            'US10Y': ['US 10Y', 'Treasury', 'Yield', 'Bonds', 'Fixed Income', '10-Year'],
            'NASDAQ': ['NASDAQ', 'Tech', 'QQQ', 'Technology', 'NAS100', 'Big Tech'],
            'S&P': ['S&P', 'SPX', 'S&P 500', 'SPY', 'US Stocks', 'Wall Street'],
            'EUR/USD': ['EURUSD', 'Euro', 'EUR', 'ECB', 'European', 'Fiber'],
            'GBP/USD': ['GBPUSD', 'Pound', 'Sterling', 'Cable', 'BOE', 'UK', 'British Pound'],
            'USD/JPY': ['USDJPY', 'Yen', 'JPY', 'BOJ', 'Dollar Yen'],
            'GBP/JPY': ['GBPJPY', 'Pound Yen', 'GJ', 'Sterling Yen'],
            'EUR/GBP': ['EURGBP', 'Euro Sterling', 'Cross', 'EUR GBP'],
            'BTC/USD': ['Bitcoin', 'BTC', 'BTCUSD', 'Crypto', 'Digital Gold'],
            'Central Banks': ['Fed', 'ECB', 'BOE', 'BOJ', 'FOMC', 'Powell', 'Lagarde', 'Bailey', 'Ueda']
        }

    def get_all_news(self, refresh=False):
        cache_key = "comprehensive_news"

        if not refresh and self.cache_manager.is_cache_valid(cache_key):
            return self.cache_manager.load_cache(cache_key)

        all_news = {}

        for asset in self.asset_keywords.keys():
            asset_news = []

            # Finnhub news
            finnhub_news = self._scan_finnhub_news(self.asset_keywords[asset])
            asset_news.extend(finnhub_news)

            # NewsAPI news
            newsapi_news = self._scan_newsapi_news(self.asset_keywords[asset])
            asset_news.extend(newsapi_news)

            # Polygon news (for applicable assets)
            if asset in ['EUR/USD', 'GBP/USD', 'USD/JPY', 'GBP/JPY', 'EUR/GBP', 'Gold', 'Oil', 'BTC/USD']:
                polygon_news = self._scan_polygon_news(asset)
                asset_news.extend(polygon_news)

            # Sort by relevance and recency
            asset_news = self._rank_news(asset_news)
            all_news[asset] = asset_news[:20]

        self.cache_manager.save_cache(all_news, cache_key)
        return all_news

    def _scan_finnhub_news(self, keywords):
        try:
            api_key = st.secrets.get("finnhub_api_key", "")
            if not api_key:
                return []

            all_articles = []

            for category in ["general", "forex", "crypto", "merger"]:
                url = f"https://finnhub.io/api/v1/news?category={category}&token={api_key}"

                try:
                    response = requests.get(url, timeout=10)
                    if response.status_code == 200:
                        articles = response.json()

                        for article in articles:
                            text = (article.get('headline', '') + ' ' + article.get('summary', '')).lower()
                            relevance = sum(1 for kw in keywords if kw.lower() in text)

                            if relevance > 0:
                                article['relevance_score'] = relevance
                                article['source_type'] = 'finnhub'
                                article['impact'] = self._assess_impact(article)
                                all_articles.append(article)

                except Exception as e:
                    continue

            return all_articles

        except Exception as e:
            return []

    def _scan_newsapi_news(self, keywords):
        try:
            api_key = st.secrets.get("newsapi_key", "")
            if not api_key:
                return []

            all_articles = []

            # Search top headlines from multiple countries
            for country in ["us", "gb", "de", "jp"]:
                url = "https://newsapi.org/v2/top-headlines"
                params = {
                    "apiKey": api_key,
                    "country": country,
                    "category": "business",
                    "pageSize": 20
                }

                try:
                    response = requests.get(url, params=params, timeout=10)
                    if response.status_code == 200:
                        data = response.json()
                        articles = data.get('articles', [])

                        for article in articles:
                            text = (article.get('title', '') + ' ' + article.get('description', '')).lower()
                            relevance = sum(1 for kw in keywords if kw.lower() in text)

                            if relevance > 0:
                                article['relevance_score'] = relevance
                                article['source_type'] = 'newsapi'
                                article['country'] = country
                                article['impact'] = self._assess_impact(article)
                                all_articles.append(article)

                except Exception as e:
                    continue

            # Also search everything for specific keywords
            for keyword in keywords[:3]:  # Limit to avoid rate limits
                url = "https://newsapi.org/v2/everything"
                params = {
                    "apiKey": api_key,
                    "q": keyword,
                    "language": "en",
                    "sortBy": "publishedAt",
                    "pageSize": 10
                }

                try:
                    response = requests.get(url, params=params, timeout=10)
                    if response.status_code == 200:
                        data = response.json()
                        articles = data.get('articles', [])

                        for article in articles:
                            article['relevance_score'] = 2
                            article['source_type'] = 'newsapi_search'
                            article['keyword_match'] = keyword
                            article['impact'] = self._assess_impact(article)
                            all_articles.append(article)

                except Exception as e:
                    pass

            return all_articles

        except Exception as e:
            return []

    def _scan_polygon_news(self, asset):
        try:
            api_key = st.secrets.get("polygon_api_key", "")
            if not api_key:
                return []

            # Map assets to Polygon tickers
            ticker_map = {
                'EUR/USD': 'C:EURUSD',
                'GBP/USD': 'C:GBPUSD',
                'USD/JPY': 'C:USDJPY',
                'GBP/JPY': 'C:GBPJPY',
                'EUR/GBP': 'C:EURGBP',
                'Gold': 'C:XAUUSD',
                'Oil': 'C:OILUSD',
                'BTC/USD': 'X:BTCUSD'
            }

            ticker = ticker_map.get(asset)
            if not ticker:
                return []

            url = f"https://api.polygon.io/v2/reference/news?ticker={ticker}&limit=20&apiKey={api_key}"

            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                articles = data.get('results', [])

                for article in articles:
                    article['relevance_score'] = 3
                    article['source_type'] = 'polygon'
                    article['ticker'] = ticker
                    article['impact'] = self._assess_impact(article)

                return articles

            return []

        except Exception as e:
            return []

    def _assess_impact(self, article):
        high_impact_words = ['crash', 'surge', 'plunge', 'spike', 'collapse', 'rally', 'crisis',
                           'emergency', 'breaking', 'unexpected', 'shock', 'record', 'intervention']
        medium_impact_words = ['rise', 'fall', 'gain', 'loss', 'increase', 'decrease', 'growth',
                             'decline', 'improve', 'worsen', 'concern', 'optimism', 'momentum']

        text = str(article).lower()

        if any(word in text for word in high_impact_words):
            return "HIGH"
        elif any(word in text for word in medium_impact_words):
            return "MEDIUM"
        else:
            return "LOW"

    def _rank_news(self, articles):
        from datetime import timezone
        def get_timestamp(article):
            for field in ['datetime', 'published_utc', 'publishedAt', 'timestamp']:
                if field in article:
                    try:
                        if isinstance(article[field], (int, float)):
                            # Always use UTC for timestamps
                            return datetime.fromtimestamp(article[field], tz=timezone.utc)
                        else:
                            dt = datetime.fromisoformat(article[field].replace('Z', '+00:00'))
                            if dt.tzinfo is None:
                                dt = dt.replace(tzinfo=timezone.utc)
                            return dt
                    except Exception:
                        pass
            # Always return aware datetime
            return (datetime.now(timezone.utc) - timedelta(days=1))

        return sorted(articles,
                     key=lambda x: (x.get('relevance_score', 0), get_timestamp(x)),
                     reverse=True)

# --- ENHANCED MARKET FORECAST GENERATOR ---
def generate_market_forecast(snapshot, all_news, econ_events, major_pairs_data=None, refresh=False):
    """Generate professional market forecast with focus on trends and speculation"""
    cache_key = f"market_forecast_{hashlib.md5(json.dumps(snapshot, sort_keys=True).encode()).hexdigest()}"

    if not refresh and CacheManager.is_cache_valid(cache_key):
        return CacheManager.load_cache(cache_key)

    # Format news digest
    news_digest = "\\n\\n".join([
        f"**{asset}**: {'; '.join([n.get('headline', n.get('title', ''))[:100] for n in news[:3]])}"
        for asset, news in all_news.items() if news
    ])[:2000]  # Limit length

    prompt = f"""You are the chief market strategist at a premier investment bank. Generate a comprehensive market forecast.

## Current Market Snapshot:
{chr(10).join([
    f"{pair.replace('_quote', '').upper()}: {snapshot.get(pair, {}).get('current', 'N/A')} ({snapshot.get(pair, {}).get('percentChange', 0):+.2f}%)"
    for pair in ['gbpjpy_quote', 'gbpusd_quote', 'eurusd_quote', 'usdjpy_quote',
                 'eurgbp_quote', 'xauusd_quote', 'nasdaq_quote', 'btcusd_quote']
    if isinstance(snapshot.get(pair, {}), dict) and snapshot.get(pair, {}).get("current") != "N/A"
])}

## Market Sentiment Indicators:
- VIX: {snapshot.get('vix_quote', {}).get('current', 'N/A')} ({snapshot.get('vix_quote', {}).get('percentChange', 0):+.1f}%)
- DXY: {snapshot.get('dxy_quote', {}).get('current', 'N/A')} ({snapshot.get('dxy_quote', {}).get('percentChange', 0):+.1f}%)

Please provide:

### 🎯 EXECUTIVE MARKET FORECAST
- 3-4 key themes driving markets today
- Risk sentiment assessment
- Major trend changes or continuations

### 📊 MAJOR PAIRS OUTLOOK

For each of these pairs, provide trend analysis:
1. **GBP/JPY** - Trend, key levels, catalyst watch
2. **GBP/USD** - Sterling outlook, BoE implications  
3. **EUR/USD** - Euro trend, ECB watch points
4. **USD/JPY** - Yen dynamics, BoJ policy impact
5. **EUR/GBP** - Cross dynamics, relative strength
6. **XAU/USD** - Safe haven flows, real yield impact
7. **NASDAQ** - Tech sector momentum
8. **BTC/USD** - Crypto sentiment

For each include:
- **Trend**: Direction (Bullish/Bearish/Consolidating)
- **Key Levels**: Support/Resistance
- **Catalyst**: What could change the trend
- **Speculation**: Market positioning

### 🔮 MARKET SPECULATION
- Contrarian opportunities
- Crowded trades at risk
- Inter-market correlations

### 📰 EVENT RISK PREVIEW
- Key releases in next 24-48 hours
- Expected volatility scenarios

Use professional terminology and clear, actionable insights."""

    try:
        if client:
            response = client.chat.completions.create(
                model="zanalytics_midas",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=2000
            )
            result = response.choices[0].message.content
            CacheManager.save_cache(result, cache_key)
            return result
        else:
            return "⚠️ OpenAI client not initialized. Please check API key."
    except Exception as e:
        return f"⚠️ Error generating forecast: {str(e)}"

# --- 3x3 GRID CHART LAYOUT ---
def create_3x3_market_grid(market_data):
    """Create a 3x3 grid of mini charts"""

    # Define subplot titles and data
    pairs = [
        ("EUR/USD", "EURUSD=X", "eurusd_quote"),
        ("GBP/USD", "GBPUSD=X", "gbpusd_quote"),
        ("USD/JPY", "USDJPY=X", "usdjpy_quote"),
        ("GBP/JPY", "GBPJPY=X", "gbpjpy_quote"),
        ("EUR/GBP", "EURGBP=X", "eurgbp_quote"),
        ("XAU/USD", "GC=F", "xauusd_quote"),
        ("NASDAQ", "^IXIC", "nasdaq_quote"),
        ("BTC/USD", "BTC-USD", "btcusd_quote"),
        ("DXY", "DX-Y.NYB", "dxy_quote")
    ]

    from plotly.subplots import make_subplots
    import numpy as np

    # Neon color scheme
    NEON_GREEN = "#00FFC6"
    NEON_RED = "#FF4B6E"
    NEON_YELLOW = "#fff700"
    # White for text
    WHITE = "#ffffff"

    fig = make_subplots(
        rows=3, cols=3,
        subplot_titles=["" for _ in pairs],  # No subplot titles
        vertical_spacing=0.09,
        horizontal_spacing=0.08,
        specs=[[{"type": "scatter"}]*3]*3
    )

    for idx, (name, ticker, key) in enumerate(pairs):
        row = idx // 3 + 1
        col = idx % 3 + 1
        no_data = False
        try:
            # Get historical data
            ticker_obj = yf.Ticker(ticker)
            hist = ticker_obj.history(period="5d", interval="1h")
            if not hist.empty:
                current_price = hist['Close'].iloc[-1]
                start_price = hist['Close'].iloc[0]
                trend_up = current_price > start_price
                color = NEON_GREEN if trend_up else NEON_RED
                # Add line trace
                fig.add_trace(
                    go.Scatter(
                        x=hist.index,
                        y=hist['Close'],
                        mode='lines',
                        name=name,
                        line=dict(width=3, color=color),
                        showlegend=False,
                        hoverinfo="skip",
                    ),
                    row=row, col=col
                )
                # Add annotation for price and % change
                if market_data and key in market_data:
                    data = market_data[key]
                    if isinstance(data, dict) and data.get('current') != 'N/A':
                        val = data.get('current')
                        # Try to get percent change (prefer percentChange, else compute)
                        pct = data.get('percentChange')
                        if pct is None:
                            prev = data.get('prev', None)
                            if prev and prev != 0:
                                pct = 100 * (val - prev) / prev
                            else:
                                pct = 0
                        # Format price string
                        price_str = f"{val:,.4f}" if isinstance(val, float) and abs(val) < 1000 else f"{val:,.2f}"
                        pct_str = f"{pct:+.2f}%"
                        # Annotation: top right, large, bold, white
                        # xref/yref
                        xref = "x domain" if idx == 0 else f"x{idx+1} domain"
                        yref = "y domain" if idx == 0 else f"y{idx+1} domain"
                        fig.add_annotation(
                            text=f"<span style='font-size:16px; font-weight:700; color:white;'>{price_str}</span><br><span style='font-size:14px; font-weight:700; color:white;'>{pct_str}</span>",
                            xref=xref,
                            yref=yref,
                            x=0.97,
                            y=0.89,
                            showarrow=False,
                            align="right",
                            font=dict(size=16, color=WHITE, family="Arial Black,Arial,sans-serif"),
                            borderpad=0,
                            bgcolor=None,
                            opacity=1,
                        )
                # Add instrument name, top left, large, bold, white
                xref = "x domain" if idx == 0 else f"x{idx+1} domain"
                yref = "y domain" if idx == 0 else f"y{idx+1} domain"
                fig.add_annotation(
                    text=f"<span style='font-size:15px; font-weight:700; color:white;'>{name}</span>",
                    xref=xref,
                    yref=yref,
                    x=0.03,
                    y=0.92,
                    showarrow=False,
                    align="left",
                    font=dict(size=15, color=WHITE, family="Arial Black,Arial,sans-serif"),
                    borderpad=0,
                    bgcolor=None,
                    opacity=1,
                )
            else:
                no_data = True
        except Exception:
            no_data = True
        if no_data:
            # Add empty line (gray)
            fig.add_trace(
                go.Scatter(
                    x=[], y=[],
                    mode='lines',
                    name=name,
                    line=dict(width=2, color="#888"),
                    showlegend=False
                ),
                row=row, col=col
            )
            # Add annotation: no data
            xref = "x domain" if idx == 0 else f"x{idx+1} domain"
            yref = "y domain" if idx == 0 else f"y{idx+1} domain"
            fig.add_annotation(
                text="<span style='font-size:14px; font-weight:700; color:white;'>No data</span>",
                xref=xref,
                yref=yref,
                x=0.5,
                y=0.5,
                showarrow=False,
                font=dict(size=14, color=WHITE, family="Arial Black,Arial,sans-serif"),
                borderpad=0,
                bgcolor=None,
                opacity=1,
            )

    # Remove all subplot backgrounds, axes, gridlines, tick labels, borders
    for i in range(1, 10):
        fig.update_xaxes(
            showgrid=False, showticklabels=False, zeroline=False, visible=False, row=(i-1)//3+1, col=(i-1)%3+1,
            showline=False, mirror=False, linewidth=0, linecolor='rgba(0,0,0,0)', ticks=""
        )
        fig.update_yaxes(
            showgrid=False, showticklabels=False, zeroline=False, visible=False, row=(i-1)//3+1, col=(i-1)%3+1,
            showline=False, mirror=False, linewidth=0, linecolor='rgba(0,0,0,0)', ticks=""
        )

    # Layout: neon yellow, large, bold, centered, no border, transparent bg
    fig.update_layout(
        height=690,
        template=None,
        title={
            'text': "<span style='font-size:30px; font-weight:800; color:#fff700; font-family:Arial Black,Arial,sans-serif'>🌍 Global Markets Overview</span>",
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 30, 'color': NEON_YELLOW, 'family': "Arial Black,Arial,sans-serif"},
        },
        showlegend=False,
        margin=dict(l=15, r=15, t=90, b=15),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
    )

    # Remove all plot frames, borders, legends
    fig.update_layout(
        legend=dict(visible=False),
        annotations=[a for a in fig.layout.annotations],
        xaxis_showgrid=False, yaxis_showgrid=False,
        xaxis_showticklabels=False, yaxis_showticklabels=False,
        xaxis_visible=False, yaxis_visible=False,
    )

    return fig

# --- ECONOMIC DATA MANAGER ---
class EconomicDataManager:
    def __init__(self):
        self.cache_manager = CacheManager()
        try:
            fred_key = st.secrets.get("fred_api_key", "")
            self.fred = Fred(api_key=fred_key) if fred_key else None
        except:
            self.fred = None

    def get_economic_calendar(self, refresh=False):
        cache_key = "economic_calendar"

        if not refresh and self.cache_manager.is_cache_valid(cache_key):
            return self.cache_manager.load_cache(cache_key)

        # Sample events for demonstration
        events = [
            {
                "time": "08:30",
                "country": "US",
                "event": "Initial Jobless Claims",
                "importance": "Medium",
                "actual": None,
                "forecast": "220K",
                "previous": "218K"
            },
            {
                "time": "10:00",
                "country": "EU",
                "event": "ECB Rate Decision",
                "importance": "High",
                "actual": None,
                "forecast": "4.25%",
                "previous": "4.25%"
            },
            {
                "time": "12:00",
                "country": "UK",
                "event": "BoE Bailey Speech",
                "importance": "High",
                "actual": None,
                "forecast": None,
                "previous": None
            },
            {
                "time": "01:00",
                "country": "JP",
                "event": "BoJ Meeting Minutes",
                "importance": "Medium",
                "actual": None,
                "forecast": None,
                "previous": None
            }
        ]

        self.cache_manager.save_cache(events, cache_key)
        return events

    def get_market_indicators(self, refresh=False):
        cache_key = "market_indicators"

        if not refresh and self.cache_manager.is_cache_valid(cache_key):
            return self.cache_manager.load_cache(cache_key)

        indicators = {}

        if self.fred:
            try:
                series_map = {
                    'CPI': 'CPIAUCSL',
                    'Unemployment': 'UNRATE',
                    'GDP': 'GDP',
                    'ISM Manufacturing': 'NAPM',
                    'Consumer Sentiment': 'UMCSENT',
                    'Housing Starts': 'HOUST'
                }

                for name, series_id in series_map.items():
                    try:
                        data = self.fred.get_series(series_id)
                        if data is not None and not data.empty:
                            latest = float(data.dropna().iloc[-1])
                            previous = float(data.dropna().iloc[-2]) if len(data.dropna()) > 1 else latest
                            indicators[name] = {
                                'value': round(latest, 2),
                                'change': round(latest - previous, 2)
                            }
                    except:
                        indicators[name] = {'value': 'N/A', 'change': 'N/A'}

                self.cache_manager.save_cache(indicators, cache_key)

            except Exception as e:
                st.warning(f"Failed to fetch indicators: {e}")

        return indicators

# --- TECHNICAL ANALYSIS ---
class TechnicalAnalyzer:
    @staticmethod
    def calculate_indicators(symbol, period="1mo"):
        try:
            ticker = yf.Ticker(symbol)
            data = ticker.history(period=period)

            if data.empty:
                return None

            # Calculate indicators
            data['SMA_20'] = data['Close'].rolling(window=20).mean()
            data['SMA_50'] = data['Close'].rolling(window=50).mean()
            data['RSI'] = TechnicalAnalyzer._calculate_rsi(data['Close'])

            # Bollinger Bands
            data['BB_middle'] = data['Close'].rolling(window=20).mean()
            bb_std = data['Close'].rolling(window=20).std()
            data['BB_upper'] = data['BB_middle'] + (bb_std * 2)
            data['BB_lower'] = data['BB_middle'] - (bb_std * 2)

            # Support and Resistance
            recent_data = data.tail(20)
            support = recent_data['Low'].min()
            resistance = recent_data['High'].max()

            # Current levels
            current_price = data['Close'].iloc[-1]

            # Trend determination
            sma20 = data['SMA_20'].iloc[-1] if not pd.isna(data['SMA_20'].iloc[-1]) else current_price
            sma50 = data['SMA_50'].iloc[-1] if not pd.isna(data['SMA_50'].iloc[-1]) else current_price

            if current_price > sma20 and sma20 > sma50:
                trend = "Strong Bullish"
            elif current_price > sma20:
                trend = "Bullish"
            elif current_price < sma20 and sma20 < sma50:
                trend = "Strong Bearish"
            elif current_price < sma20:
                trend = "Bearish"
            else:
                trend = "Neutral"

            return {
                'current': round(current_price, 4),
                'sma_20': round(sma20, 4),
                'sma_50': round(sma50, 4) if not pd.isna(data['SMA_50'].iloc[-1]) else None,
                'rsi': round(data['RSI'].iloc[-1], 2) if not pd.isna(data['RSI'].iloc[-1]) else None,
                'bb_upper': round(data['BB_upper'].iloc[-1], 4) if not pd.isna(data['BB_upper'].iloc[-1]) else None,
                'bb_lower': round(data['BB_lower'].iloc[-1], 4) if not pd.isna(data['BB_lower'].iloc[-1]) else None,
                'support': round(support, 4),
                'resistance': round(resistance, 4),
                'trend': trend,
                'data': data  # Include raw data for charting
            }

        except Exception as e:
            return None

    @staticmethod
    def _calculate_rsi(prices, period=14):
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

# --- MAIN DASHBOARD ---
def main():
    # Apply advanced styling
    st.markdown(apply_advanced_styling(), unsafe_allow_html=True)

    # Initialize components
    news_scanner = ComprehensiveNewsScanner()
    econ_manager = EconomicDataManager()
    tech_analyzer = TechnicalAnalyzer()

    # Check for cache on page load
    if st.session_state.last_refresh is None:
        # First load - check if we have valid cache
        if CacheManager.is_cache_valid("comprehensive_news") and CacheManager.is_cache_valid("market_snapshot"):
            st.session_state.last_refresh = datetime.fromtimestamp(
                os.path.getmtime(CacheManager.get_cache_path("market_snapshot"))
            )

    # (Removed Elite Trading Desk Pro banner header for Market Overview tab)

    # Control bar
    col1, col2, col3 = st.columns([2, 6, 2])
    with col1:
        if st.session_state.last_refresh:
            st.info(f"📅 {st.session_state.last_refresh.strftime('%H:%M:%S')}")

    with col3:
        if st.button("🔄 Refresh All", key="main_refresh", use_container_width=True):
            CacheManager.clear_cache()
            st.session_state.last_refresh = datetime.now()
            st.rerun()

    # Auto-refresh check
    if st.session_state.auto_refresh_enabled:
        if not st.session_state.last_refresh or (datetime.now() - st.session_state.last_refresh).seconds > 300:
            st.session_state.last_refresh = datetime.now()
            st.rerun()

    # Sidebar
    with st.sidebar:
        st.markdown("""
            <div style='background: linear-gradient(135deg, #1a237e 0%, #3949ab 100%); 
                        padding: 1.5rem; 
                        border-radius: 15px; 
                        margin-bottom: 1rem;'>
                <h3 style='color: white; margin: 0;'>⚙️ Control Center</h3>
            </div>
        """, unsafe_allow_html=True)

        st.session_state.auto_refresh_enabled = st.checkbox(
            "⏰ Auto-refresh (5 min)",
            value=st.session_state.auto_refresh_enabled
        )

        st.markdown("### 📦 Cache Status")

        cache_items = [
            ("📰 News", "comprehensive_news"),
            ("📊 Market Data", "market_snapshot"),
            ("🔮 Forecast", "market_forecast_*"),
            ("📅 Calendar", "economic_calendar")
        ]

        for name, key in cache_items:
            if key.endswith('*'):
                import glob
                files = glob.glob(os.path.join(CACHE_DIR, f"{key}.pkl"))
                valid = any(CacheManager.is_cache_valid(os.path.basename(f)[:-4]) for f in files)
            else:
                valid = CacheManager.is_cache_valid(key)

            status = "✅" if valid else "❌"
            st.write(f"{status} {name}")

        if st.button("🗑️ Clear All Cache", use_container_width=True):
            CacheManager.clear_cache()
            st.success("✅ Cache cleared!")

    # Main content tabs
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📈 Market Overview",
        "📰 News Center",
        "📊 Technical Analysis",
        "📅 Economic Calendar",
        "🔮 Market Forecast",
        "⚡ Risk Dashboard"
    ])

    # Tab 1: Market Overview
    with tab1:
        # --- Macro Dashboard Grid: 3x5 Professional Macro Set ---
        macro_grid = [
            ("DXY", "dxy_quote"),
            ("VIX", "vix_quote"),
            ("EUR/USD", "eurusd_quote"),
            ("GBP/USD", "gbpusd_quote"),
            ("USD/JPY", "usdjpy_quote"),
            ("USD/CAD", "usdcad_quote"),
            ("AUD/USD", "audusd_quote"),
            ("USD/CHF", "usdchf_quote"),
            ("EUR/GBP", "eurgbp_quote"),
            ("GBP/JPY", "gbpjpy_quote"),
            ("US 10Y", "us10y_quote"),
            ("GE 10Y", "ge10y_quote"),
            ("JP 10Y", "jp10y_quote"),
            ("Gold", "gold_quote"),
            ("Oil", "oil_quote"),
        ]
        rows, cols = 3, 5
        macro_grid_rows = [st.columns(cols, gap="large") for _ in range(rows)]
        # Update snapshot to include all needed keys
        symbol_map = {
            "dxy_quote": "DX-Y.NYB",
            "vix_quote": "^VIX",
            "eurusd_quote": "EURUSD=X",
            "gbpusd_quote": "GBPUSD=X",
            "usdjpy_quote": "USDJPY=X",
            "usdcad_quote": "USDCAD=X",
            "audusd_quote": "AUDUSD=X",
            "usdchf_quote": "USDCHF=X",
            "eurgbp_quote": "EURGBP=X",
            "gbpjpy_quote": "GBPJPY=X",
            "us10y_quote": "^TNX",
            "ge10y_quote": "DE10Y-DE.BD",
            "jp10y_quote": "JP10Y-JP.BD",
            "gold_quote": "GC=F",
            "oil_quote": "CL=F",
        }
        # Get or load snapshot
        if CacheManager.is_cache_valid("market_snapshot") and not st.button("🔄 Refresh Prices", key="refresh_prices"):
            snapshot = CacheManager.load_cache("market_snapshot")
        else:
            with st.spinner("Fetching market data..."):
                snapshot = get_prices(symbol_map)
                CacheManager.save_cache(snapshot, "market_snapshot")
        # Macro grid display
        ticker_map = {
            "dxy_quote": "DX-Y.NYB",
            "vix_quote": "^VIX",
            "eurusd_quote": "EURUSD=X",
            "gbpusd_quote": "GBPUSD=X",
            "usdjpy_quote": "USDJPY=X",
            "usdcad_quote": "USDCAD=X",
            "audusd_quote": "AUDUSD=X",
            "usdchf_quote": "USDCHF=X",
            "eurgbp_quote": "EURGBP=X",
            "gbpjpy_quote": "GBPJPY=X",
            "us10y_quote": "^TNX",
            "ge10y_quote": "DE10Y-DE.BD",
            "jp10y_quote": "JP10Y-JP.BD",
            "gold_quote": "GC=F",
            "oil_quote": "CL=F",
        }
        for idx, (label, key) in enumerate(macro_grid):
            row = idx // cols
            col = idx % cols
            with macro_grid_rows[row][col]:
                data = snapshot.get(key, {})
                val = data.get("current", "—")
                # prefer 'change' for delta, fallback to percentChange
                delta = data.get("change", data.get("percentChange", 0))
                try:
                    delta_f = float(delta)
                except Exception:
                    delta_f = 0.0
                delta_up = delta_f > 0
                delta_color = "#10b981" if delta_up else "#ef4444"
                delta_icon = "▲" if delta_up else "▼"
                # --- LABEL TOP ---
                st.markdown(f"<div style='color:#e0e7ef;font-size:1.04rem;opacity:0.83;margin-bottom:0.08rem;font-weight:700;'>{label}</div>", unsafe_allow_html=True)
                # --- BIG VALUE ---
                st.markdown(f"<div style='font-size:2.2rem;font-weight:800;color:#fff;'>{val if val != '—' else '—'}</div>", unsafe_allow_html=True)
                # --- DELTA ---
                st.markdown(f"<div style='font-size:1.13rem;font-weight:700;color:{delta_color};margin-bottom:0.22rem;'>{delta_icon} {delta_f:+.2f}</div>", unsafe_allow_html=True)
                # --- SPARKLINE ---
                ticker = ticker_map.get(key)
                yvals = []
                try:
                    # For DE 10Y and JP 10Y, use synthetic/static sparkline
                    if key == "ge10y_quote":
                        # Synthetic (e.g., gently rising line with some noise)
                        base = 2.5
                        np.random.seed(42)
                        yvals = base + np.cumsum(np.random.normal(0, 0.01, 30))
                    elif key == "jp10y_quote":
                        base = 0.9
                        np.random.seed(43)
                        yvals = base + np.cumsum(np.random.normal(0, 0.003, 30))
                    elif ticker:
                        hist = yf.Ticker(ticker).history(period="1mo")
                        yvals = hist["Close"].dropna().values[-30:]
                    if yvals is not None and len(yvals) > 2:
                        xvals = list(range(len(yvals)))
                        fig = go.Figure()
                        fig.add_trace(go.Scatter(
                            x=xvals, y=yvals, mode="lines",
                            line=dict(color="#FFD600", width=2.5),
                            showlegend=False, hoverinfo="skip",
                        ))
                        fig.update_layout(
                            margin=dict(l=0, r=0, t=8, b=0), height=52, width=170,
                            paper_bgcolor="rgba(0,0,0,0)",
                            plot_bgcolor="rgba(0,0,0,0)",
                        )
                        fig.update_xaxes(visible=False, showgrid=False, zeroline=False)
                        fig.update_yaxes(visible=False, showgrid=False, zeroline=False)
                        st.plotly_chart(fig, use_container_width=True)
                except Exception:
                    pass

        # --- Macro Outlook / Commentary ---
        st.markdown("#### 🌐 Macro Outlook")
        st.markdown("""
<div style="font-size:1.1rem; color:#e0e7ef; background:rgba(26,29,58,0.45); border-radius:10px; padding:1.2rem 1.4rem; margin-bottom:1.3rem; font-weight:500;">
<b>Risk sentiment is mixed as the market digests the latest central bank policy signals, with US yields stable and dollar pairs fluctuating. Commodity prices remain in focus amid ongoing geopolitical tensions. Watch for US jobs data, ECB commentary, and volatility in risk assets.</b>
</div>
""", unsafe_allow_html=True)

        # --- Macro News (styled, like Tab 2) ---
        st.markdown("#### 📰 Macro News")
        news_limit = 6
        # Use EUR/USD, GBP/USD, Gold, Oil, US 10Y, VIX, DXY for focus
        macro_assets = ["EUR/USD", "GBP/USD", "Gold", "Oil", "US10Y", "VIX", "DXY"]
        for asset in macro_assets:
            asset_news = news_scanner.get_all_news().get(asset, [])[:news_limit]
            if asset_news:
                st.markdown(f"<div style='font-size:1.05rem; color:#e0e7ef; font-weight:600; margin-top:0.7rem; margin-bottom:0.15rem;'>{asset}</div>", unsafe_allow_html=True)
                for article in asset_news:
                    impact = article.get('impact', 'LOW')
                    impact_class = f"{impact.lower()}-impact"
                    impact_emoji = {'HIGH': '🔴', 'MEDIUM': '🟡', 'LOW': '🟢'}.get(impact, '🟢')
                    summary = article.get('summary', article.get('description', ''))
                    headline = article.get('headline', article.get('title', ''))
                    url = article.get('url', article.get('link', '#'))
                    st.markdown(
                        f"""
                        <div class="news-item {impact_class}">
                            <span style='font-size:1.15rem;'>{impact_emoji}</span>
                            <a href="{url}" target="_blank" style="color:#93c5fd; text-decoration:none; font-weight:600;">{headline}</a>
                            {'<br><span style="font-size:0.97rem; color:#b5b5be;">'+summary+'</span>' if summary and summary != headline else ''}
                        </div>
                        """, unsafe_allow_html=True)

    # Tab 2: News Center
    with tab2:
        st.markdown("### 📰 Comprehensive News Center")

        # Get all news
        if st.button("🔄 Refresh News", key="refresh_news"):
            all_news = news_scanner.get_all_news(refresh=True)
        else:
            all_news = news_scanner.get_all_news(refresh=False)

        # News controls
        col1, col2, col3 = st.columns([4, 2, 2])

        with col1:
            selected_assets = st.multiselect(
                "Filter by Asset",
                options=list(all_news.keys()),
                default=["EUR/USD", "GBP/USD", "Gold", "Central Banks", "GBP/JPY"]
            )

        with col2:
            news_count = st.slider("News per asset", 1, 10, 5)

        with col3:
            show_summaries = st.checkbox("Show summaries", True)

        # Display news
        for asset in selected_assets:
            if asset in all_news:
                st.markdown(f'#### 📰 {asset}')

                asset_news = all_news[asset][:news_count]

                if asset_news:
                    for article in asset_news:
                        impact = article.get('impact', 'LOW')
                        impact_class = f"{impact.lower()}-impact"
                        impact_emoji = {'HIGH': '🔴', 'MEDIUM': '🟡', 'LOW': '🟢'}.get(impact, '🟢')

                        with st.container():
                            st.markdown('</div>', unsafe_allow_html=True)

    # Tab 3: Technical Analysis
    with tab3:
        st.markdown('<div class="technical-section">', unsafe_allow_html=True)

        st.header("📊 Technical Analysis Dashboard")

        # Symbol selection
        col1, col2 = st.columns([3, 1])
        with col1:
            selected_symbol = st.selectbox(
                "Select Instrument",
                options=[
                    ("EUR/USD", "EURUSD=X"),
                    ("GBP/USD", "GBPUSD=X"),
                    ("USD/JPY", "USDJPY=X"),
                    ("GBP/JPY", "GBPJPY=X"),
                    ("EUR/GBP", "EURGBP=X"),
                    ("Gold", "GC=F"),
                    ("S&P 500", "^GSPC"),
                    ("NASDAQ", "^IXIC"),
                    ("Bitcoin", "BTC-USD"),
                    ("Oil", "CL=F")
                ],
                format_func=lambda x: x[0]
            )

        with col2:
            period = st.selectbox(
                "Period",
                ["1d", "5d", "1mo", "3mo", "6mo", "1y"]
            )

        if selected_symbol:
            symbol_name, symbol_ticker = selected_symbol

            # Get technical indicators
            tech_data = tech_analyzer.calculate_indicators(symbol_ticker, period)

            if tech_data:
                # Display key metrics
                col1, col2, col3, col4 = st.columns(4)

                with col1:
                    st.markdown('<div class="technical-metric">', unsafe_allow_html=True)
                    st.metric("Current Price", f"{tech_data['current']:.4f}")
                    st.caption(f"Trend: {tech_data['trend']}")
                    st.markdown('</div>', unsafe_allow_html=True)

                with col2:
                    if tech_data['rsi']:
                        rsi_color = "🔴" if tech_data['rsi'] > 70 else "🟢" if tech_data['rsi'] < 30 else "🟡"
                        st.markdown('<div class="technical-metric">', unsafe_allow_html=True)
                        st.metric("RSI", f"{tech_data['rsi']:.2f}")
                        st.caption(f"{rsi_color} {'Overbought' if tech_data['rsi'] > 70 else 'Oversold' if tech_data['rsi'] < 30 else 'Neutral'}")
                        st.markdown('</div>', unsafe_allow_html=True)

                with col3:
                    st.markdown('<div class="technical-metric">', unsafe_allow_html=True)
                    st.metric("Support", f"{tech_data['support']:.4f}")
                    st.caption("Key level")
                    st.markdown('</div>', unsafe_allow_html=True)

                with col4:
                    st.markdown('<div class="technical-metric">', unsafe_allow_html=True)
                    st.metric("Resistance", f"{tech_data['resistance']:.4f}")
                    st.caption("Key level")
                    st.markdown('</div>', unsafe_allow_html=True)

                # Create technical chart
                ticker = yf.Ticker(symbol_ticker)
                hist = ticker.history(period=period)

                if not hist.empty:
                    # Create candlestick chart with indicators
                    fig = go.Figure()

                    # Add candlestick
                    fig.add_trace(go.Candlestick(
                        x=hist.index,
                        open=hist['Open'],
                        high=hist['High'],
                        low=hist['Low'],
                        close=hist['Close'],
                        name='Price'
                    ))

                    # Add SMA lines
                    if tech_data['sma_20']:
                        sma_20 = hist['Close'].rolling(window=20).mean()
                        fig.add_trace(go.Scatter(
                            x=hist.index,
                            y=sma_20,
                            mode='lines',
                            name='SMA 20',
                            line=dict(color='#3b82f6', width=2)
                        ))

                    if tech_data['sma_50'] and len(hist) >= 50:
                        sma_50 = hist['Close'].rolling(window=50).mean()
                        fig.add_trace(go.Scatter(
                            x=hist.index,
                            y=sma_50,
                            mode='lines',
                            name='SMA 50',
                            line=dict(color='#8b5cf6', width=2)
                        ))

                    # Add support and resistance lines
                    fig.add_hline(y=tech_data['support'],
                                 line_dash="dash",
                                 line_color="green",
                                 annotation_text="Support")

                    fig.add_hline(y=tech_data['resistance'],
                                 line_dash="dash",
                                 line_color="red",
                                 annotation_text="Resistance")

                    fig.update_layout(
                        title=f"{symbol_name} Technical Analysis",
                        xaxis_title="Date",
                        yaxis_title="Price",
                        template="plotly_dark",
                        height=600,
                        xaxis_rangeslider_visible=False
                    )

                    st.plotly_chart(fig, use_container_width=True)

                    # Volume chart
                    volume_fig = go.Figure()
                    colors = ['red' if hist['Close'].iloc[i] < hist['Open'].iloc[i]
                             else 'green' for i in range(len(hist))]

                    volume_fig.add_trace(go.Bar(
                        x=hist.index,
                        y=hist['Volume'],
                        marker_color=colors,
                        name='Volume'
                    ))

                    volume_fig.update_layout(
                        title="Volume",
                        xaxis_title="Date",
                        yaxis_title="Volume",
                        template="plotly_dark",
                        height=200
                    )

                    st.plotly_chart(volume_fig, use_container_width=True)

                # Moving average signals
                st.subheader("📈 Moving Average Signals")
                ma_signals = []

                if tech_data['sma_20'] and tech_data['current']:
                    signal = "BUY" if tech_data['current'] > tech_data['sma_20'] else "SELL"
                    ma_signals.append({
                        'Indicator': 'Price vs SMA 20',
                        'Value': f"{tech_data['current']:.4f} vs {tech_data['sma_20']:.4f}",
                        'Signal': signal,
                        'Strength': 'Strong' if abs(tech_data['current'] - tech_data['sma_20']) / tech_data['sma_20'] > 0.02 else 'Weak'
                    })

                if ma_signals:
                    signals_df = pd.DataFrame(ma_signals)
                    st.dataframe(signals_df, hide_index=True, use_container_width=True)

            else:
                st.error("Failed to fetch technical data")

        st.markdown('</div>', unsafe_allow_html=True)

    # Tab 4: Economic Calendar
    with tab4:
        st.markdown('<div class="forecast-section">', unsafe_allow_html=True)

        st.header("📅 Economic Calendar & Indicators")

        # Economic events
        events = econ_manager.get_economic_calendar(
            refresh=st.button("🔄 Refresh Calendar", key="refresh_calendar")
        )

        if events:
            st.subheader("🗓️ Today's Key Events")

            # Create events dataframe
            events_df = pd.DataFrame(events)

            # Style by importance
            def style_importance(val):
                if val == "High":
                    return 'background-color: #f38ba8; color: white;'
                elif val == "Medium":
                    return 'background-color: #fab387; color: black;'
                else:
                    return 'background-color: #a6e3a1; color: black;'

            styled_events = events_df.style.applymap(
                style_importance,
                subset=['importance']
            )

            st.dataframe(styled_events, hide_index=True, use_container_width=True)

        # Economic indicators
        st.subheader("📊 Key Economic Indicators")

        indicators = econ_manager.get_market_indicators(
            refresh=st.button("🔄 Refresh Indicators", key="refresh_indicators")
        )

        if indicators:
            # Display in grid
            cols = st.columns(3)

            for idx, (name, data) in enumerate(indicators.items()):
                col = cols[idx % 3]

                with col:
                    st.markdown('<div class="forecast-metric">', unsafe_allow_html=True)

                    if data['value'] != 'N/A':
                        change_str = f"{data['change']:+.2f}" if data['change'] != 'N/A' else "N/A"
                        st.metric(
                            name,
                            f"{data['value']}",
                            change_str
                        )
                    else:
                        st.metric(name, "N/A", "N/A")

                    st.markdown('</div>', unsafe_allow_html=True)

        # Calendar visualization
        st.subheader("📈 Economic Events Impact Analysis")

        if events:
            impact_counts = {"High": 0, "Medium": 0, "Low": 0}
            for event in events:
                impact_counts[event.get('importance', 'Low')] += 1

            # Create pie chart
            fig = go.Figure(data=[go.Pie(
                labels=list(impact_counts.keys()),
                values=list(impact_counts.values()),
                hole=.3,
                marker_colors=['#f38ba8', '#fab387', '#a6e3a1']
            )])

            fig.update_layout(
                title="Event Impact Distribution",
                template="plotly_dark",
                height=300
            )

            st.plotly_chart(fig, use_container_width=True)

        st.markdown('</div>', unsafe_allow_html=True)

    # Tab 5: Market Forecast
    with tab5:
        st.markdown('<div class="forecast-section">', unsafe_allow_html=True)
        st.markdown("#### 🔮 Market Forecast & Trading Themes")

        # === 1. Narrative Macro Forecast ===
        forecast_assets = [
            ("DXY", "dxy_quote", "DX-Y.NYB"),
            ("EUR/USD", "eurusd_quote", "EURUSD=X"),
            ("GBP/USD", "gbpusd_quote", "GBPUSD=X"),
            ("USD/JPY", "usdjpy_quote", "USDJPY=X"),
            ("Gold", "gold_quote", "GC=F"),
            ("Oil", "oil_quote", "CL=F"),
            ("S&P 500", "spx_quote", "^GSPC"),
            ("NASDAQ", "nasdaq_quote", "^IXIC"),
            ("Bitcoin", "btcusd_quote", "BTC-USD"),
        ]
        all_news = news_scanner.get_all_news(refresh=False)
        asset_snapshot = {k: snapshot.get(k, {}) for _, k, _ in forecast_assets}

        # == MACRO NARRATIVE SECTION ==
        macro_forecast = ""
        try:
            # Full context macro forecast (AI powered)
            macro_prompt = f"""
You are a senior macro strategist at a top-tier investment bank. Write this morning's note in 3 tight sections:

1. **Market Movers & Macro Drivers:** Bullet points, covering FX (DXY, EUR/USD, GBP/USD, JPY), Rates, Commodities, Equities, Risk (VIX) -- always cite specific prices and % moves.
2. **Key Macro Themes:** List 2-3 major themes or regime changes, with short justification and cross-asset links (e.g. "Dollar strength on Fed hawkishness", "Risk-on after US CPI").
3. **Actionable Trade Ideas & Risk Scenarios:** Bullet actionable ideas with entry/risk, highlight crowded trades, and what could break current consensus.

Use this latest data snapshot:
{json.dumps({k: snapshot.get(k, {}) for _, k, _ in forecast_assets}, indent=2)}
Sample headlines: {', '.join([n[0].get('headline','') for n in all_news.values() if n])}
"""
            if client:
                resp = client.chat.completions.create(
                    model="g-5wVuKfpEt-stocks-crypto-options-forex-market-summary",
                    messages=[{"role": "user", "content": macro_prompt}],
                    temperature=0.33, max_tokens=1024,
                )
                macro_forecast = resp.choices[0].message.content.strip()
        except Exception:
            macro_forecast = ""

        # Fallback if AI fails
        if not macro_forecast:
            macro_forecast = """
- **FX:** Dollar firm (DXY above 105), EUR/USD weak below 1.08, GBP/USD stable near 1.27 as US data and central bank rhetoric drive flows.
- **Rates:** US 10Y yield steady above 4.2%, risk appetite mixed; volatility low (VIX ~14).
- **Commodities:** Gold rangebound near $2350, Oil under pressure but OPEC cuts in focus.
- **Equities:** NASDAQ still leading global risk but breadth narrowing, watch for rotation.

**Themes:** (1) Dollar demand on US macro resilience (2) Divergence in central bank messaging (3) Stagnant commodities, awaiting catalyst.

**Trade/risk:** Fade EUR/USD rallies, gold buy on dips, caution on late-cycle tech chase.
            """

        st.markdown(
            f"<div style='background:rgba(255,255,120,0.08);border-radius:10px;padding:1.05em 1.1em;margin-bottom:1.1em;color:#ffe082;font-size:1.09em;font-weight:600;border:1.5px solid #fff700;'>"
            f"{macro_forecast}"
            f"</div>", unsafe_allow_html=True
        )

        # === 2. Macro Table (optional) ===
        st.markdown("##### Cross-Asset Macro Table")
        macro_table_md = "| Asset | Price | Δ % | Trend |\n|---|---|---|---|\n"
        for label, key, _ in forecast_assets:
            data = snapshot.get(key, {})
            price = data.get('current', 'N/A')
            pct = data.get('percentChange', 0)
            trend = "↑" if pct > 0 else "↓" if pct < 0 else "→"
            macro_table_md += f"| {label} | {price} | {pct:+.2f}% | {trend} |\n"
        st.markdown(macro_table_md)

        # === 3. Asset Towel Grid (deeper) ===
        st.markdown("##### Key Asset Themes & Trade Setups")
        st.markdown("<style>.towel-grid-row{display:flex;align-items:center;margin-bottom:0.65em;gap:1.2em;} .towel-metric{width:105px;} .towel-spark{min-width:135px;max-width:150px;}</style>", unsafe_allow_html=True)

        for label, key, ticker in forecast_assets:
            data = snapshot.get(key, {})
            price = data.get('current', 'N/A')
            pct = data.get('percentChange', 0)
            pct_str = f"{pct:+.2f}%" if isinstance(pct, (int, float)) else pct
            # Sparkline
            try:
                hist = yf.Ticker(ticker).history(period="1mo")
                yvals = hist["Close"].dropna().values[-30:]
                xvals = list(range(len(yvals)))
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=xvals, y=yvals, mode="lines", line=dict(width=2.2), showlegend=False, hoverinfo="skip"))
                fig.update_layout(margin=dict(l=0, r=0, t=4, b=0), height=44, width=140, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
                fig.update_xaxes(visible=False)
                fig.update_yaxes(visible=False)
            except Exception:
                fig = None
            # AI-generated asset comment
            asset_summary = ""
            try:
                prompt = f"Asset: {label}\nCurrent price: {price} ({pct_str})\nTop headline: {all_news.get(label, [{}])[0].get('headline','')}\nIn 2 sentences, give an institutional theme or actionable view. Reference price action."
                if client:
                    resp = client.chat.completions.create(
                        model="g-5wVuKfpEt-stocks-crypto-options-forex-market-summary",
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0.25, max_tokens=120,
                    )
                    asset_summary = resp.choices[0].message.content.strip()
            except Exception:
                asset_summary = ""
            # Top news
            headlines = all_news.get(label, [])
            headline = headlines[0].get("headline", "") if headlines else ""
            url = headlines[0].get("url", "#") if headlines else "#"

            st.markdown(f"<div class='towel-grid-row'>"
                        f"<div class='towel-metric'><b>{label}</b><br>{price} <span style='font-size:0.93em;color:#ddd;'>{pct_str}</span></div>", unsafe_allow_html=True)
            if fig:
                st.plotly_chart(fig, use_container_width=False, config={'displayModeBar': False})
            else:
                st.markdown("<div class='towel-spark'>n/a</div>", unsafe_allow_html=True)
            st.markdown(f"<div style='flex:2;'><span style='color:#ffe082;font-weight:600'>{asset_summary}</span>", unsafe_allow_html=True)
            if headline:
                st.markdown(f"<br><span style='font-size:0.96em;color:#8ab4f8;'>📰 <a href='{url}' target='_blank' style='color:#8ab4f8;'>{headline}</a></span>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # Tab 6: Risk Dashboard
    with tab6:
        st.markdown('<div class="risk-section">', unsafe_allow_html=True)

        st.header("⚡ Risk Management Dashboard")

        # Risk metrics
        col1, col2, col3 = st.columns(3)

        # VIX-based risk assessment
        vix_val = snapshot.get("vix_quote", {}).get("current", 20)
        if vix_val != "N/A":
            risk_score = min(100, (vix_val / 40) * 100)

            with col1:
                st.markdown('<div class="risk-metric">', unsafe_allow_html=True)
                st.metric(
                    "Market Risk Score",
                    f"{risk_score:.0f}/100",
                    f"{'+' if snapshot.get('vix_quote', {}).get('percentChange', 0) > 0 else ''}{snapshot.get('vix_quote', {}).get('percentChange', 0):.1f}%"
                )

                # Risk gauge
                fig = go.Figure(go.Indicator(
                    mode="gauge+number",
                    value=risk_score,
                    domain={'x': [0, 1], 'y': [0, 1]},
                    title={'text': "Risk Level"},
                    gauge={
                        'axis': {'range': [None, 100]},
                        'bar': {'color': "darkred" if risk_score > 70 else "orange" if risk_score > 40 else "green"},
                        'steps': [
                            {'range': [0, 40], 'color': "lightgreen"},
                            {'range': [40, 70], 'color': "lightyellow"},
                            {'range': [70, 100], 'color': "lightcoral"}
                        ],
                        'threshold': {
                            'line': {'color': "red", 'width': 4},
                            'thickness': 0.75,
                            'value': 90
                        }
                    }
                ))

                fig.update_layout(
                    height=250,
                    template="plotly_dark",
                    margin=dict(l=20, r=20, t=40, b=20)
                )

                st.plotly_chart(fig, use_container_width=True)
                st.markdown('</div>', unsafe_allow_html=True)

        # Correlation matrix
        with col2:
            st.markdown('<div class="risk-metric">', unsafe_allow_html=True)
            st.subheader("🔗 Asset Correlations")

            # Sample correlation data
            corr_assets = ["EUR/USD", "GBP/USD", "Gold", "Oil", "S&P"]
            corr_matrix = pd.DataFrame(
                np.random.rand(5, 5) * 2 - 1,
                index=corr_assets,
                columns=corr_assets
            )
            np.fill_diagonal(corr_matrix.values, 1)

            # Make it symmetric
            corr_matrix = (corr_matrix + corr_matrix.T) / 2

            fig = go.Figure(data=go.Heatmap(
                z=corr_matrix.values,
                x=corr_assets,
                y=corr_assets,
                colorscale='RdBu',
                zmid=0
            ))

            fig.update_layout(
                height=300,
                template="plotly_dark",
                margin=dict(l=40, r=40, t=40, b=40)
            )

            st.plotly_chart(fig, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

        # Position sizing calculator
        with col3:
            st.markdown('<div class="risk-metric">', unsafe_allow_html=True)
            st.subheader("📊 Position Sizing")

            account_size = st.number_input("Account Size ($)", value=10000, step=1000)
            risk_percent = st.slider("Risk per Trade (%)", 0.5, 5.0, 2.0, 0.5)
            stop_loss_pips = st.number_input("Stop Loss (pips)", value=50, step=5)

            risk_amount = account_size * (risk_percent / 100)
            position_size = (risk_amount / stop_loss_pips) * 10000  # Standard lot calculation

            st.metric("Risk Amount", f"${risk_amount:.2f}")
            st.metric("Position Size", f"{position_size:.0f} units")
            st.metric("Lots", f"{position_size/100000:.2f}")

            st.markdown('</div>', unsafe_allow_html=True)

        # Risk warnings
        st.subheader("⚠️ Risk Alerts")

        risk_alerts = []

        # --- PATCH: AI-driven risk warning via custom GPT ---
        ai_risk_summary = None
        try:
            if client:
                # Compose prompt to the Market Summary GPT
                prompt = f'''You are a professional trading risk analyst. Given this market snapshot, highlight any risk alerts, tail risks, and actionable warnings across FX, indices, crypto, and commodities.
Market snapshot (core assets):
{json.dumps({k: snapshot.get(k, {}) for k in ["dxy_quote", "vix_quote", "eurusd_quote", "gbpusd_quote", "usdjpy_quote", "gbpjpy_quote", "gold_quote", "oil_quote", "spx_quote", "nasdaq_quote", "btcusd_quote"]}, indent=2)}

Only include risk situations and actionable warnings relevant for today's session. Respond in concise bullet points, and only if there is real risk.'''
                # Use the Market Summary GPT or fallback to default if unavailable
                response = client.chat.completions.create(
                    model="zanalytics_midas",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3,
                    max_tokens=800
                )
                ai_risk_summary = response.choices[0].message.content.strip()
        except Exception as e:
            ai_risk_summary = None

        # Standard risk checks as fallback
        if ai_risk_summary:
            st.markdown("#### 🤖 AI Risk Summary")
            st.markdown(f"<div style='font-size:1.11rem; background:rgba(255,255,50,0.10); border-radius:8px; padding:0.8em 1em; color:#fff; margin-bottom:0.8em;'>{ai_risk_summary}</div>", unsafe_allow_html=True)

        # --- Legacy risk alert logic ---
        if vix_val != "N/A" and vix_val > 25:
            risk_alerts.append({
                'Level': '🔴 HIGH',
                'Alert': f'VIX above 25 ({vix_val:.2f}) - Elevated market volatility',
                'Action': 'Consider reducing position sizes'
            })

        # Check for large moves
        for asset, data in snapshot.items():
            if isinstance(data, dict) and data.get('percentChange'):
                if abs(data['percentChange']) > 2:
                    risk_alerts.append({
                        'Level': '🟡 MEDIUM',
                        'Alert': f"{asset.replace('_quote', '').upper()} moved {data['percentChange']:+.2f}%",
                        'Action': 'Monitor for continuation or reversal'
                    })

        if risk_alerts:
            alerts_df = pd.DataFrame(risk_alerts)
            st.dataframe(alerts_df, hide_index=True, use_container_width=True)
        else:
            st.success("✅ No significant r  isk alerts at this time")

        st.markdown('</div>', unsafe_allow_html=True)

# Run the app
if __name__ == "__main__":
    main()
