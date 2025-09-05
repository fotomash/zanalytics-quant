import os
from typing import Optional, Dict

import pandas as pd
import requests


class Mt5APIClient:
    """Simple client for the MT5 HTTP API."""

    def __init__(self, base_url: Optional[str] = None, timeout: int = 10):
        self.base_url = base_url or os.getenv("MT5_API_URL", "http://localhost:5001")
        self.timeout = timeout

    def _get(self, path: str, params: Optional[Dict] = None):
        url = f"{self.base_url.rstrip('/')}/{path.lstrip('/')}"
        resp = requests.get(url, params=params, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()

    def get_ticks(self, symbol: str, limit: int = 1000) -> pd.DataFrame:
        data = self._get("ticks", params={"symbol": symbol, "limit": limit})
        df = pd.DataFrame(data)
        if "time" in df.columns:
            df.rename(columns={"time": "timestamp"}, inplace=True)
            df["timestamp"] = pd.to_datetime(df["timestamp"])
        return df

    def get_bars(self, symbol: str, timeframe: str, limit: int = 200) -> pd.DataFrame:
        data = self._get(f"bars/{symbol}/{timeframe}", params={"limit": limit})
        df = pd.DataFrame(data)
        if "time" in df.columns:
            df.rename(columns={"time": "timestamp"}, inplace=True)
            df["timestamp"] = pd.to_datetime(df["timestamp"])
        return df
