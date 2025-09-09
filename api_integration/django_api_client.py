import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Union

import pandas as pd
import requests
from requests.adapters import HTTPAdapter, Retry

class DjangoAPIClient:
    """
    Client for interacting with the Django API endpoints.
    This class provides methods to fetch data that was previously loaded from parquet files.
    """

    def __init__(self, base_url: Optional[str] = None, *, token: Optional[str] = None,
                 api_prefix: Optional[str] = None, timeout: int = 5,
                 retries: int = 3, backoff_factor: float = 0.3):
        """Initialize the API client.

        Args:
            base_url: Base URL for the Django API. If ``None`` uses ``DJANGO_API_URL``.
            token: API token. If ``None`` uses ``DJANGO_API_TOKEN``.
            api_prefix: Prefix for all API endpoints. Defaults to ``/api/v1``.
            timeout: Request timeout in seconds.
            retries: Number of retries for failed requests.
            backoff_factor: Backoff factor for retries.
        """
        self.base_url = base_url or os.getenv('DJANGO_API_URL', 'http://django:8000')
        self.api_prefix = api_prefix or os.getenv('DJANGO_API_PREFIX', '/api/v1')
        self.token = token or os.getenv('DJANGO_API_TOKEN')
        self.timeout = timeout
        self.logger = logging.getLogger(__name__)

        self.session = requests.Session()
        if self.token:
            self.session.headers.update({'Authorization': f'Token {self.token}'})

        retry_strategy = Retry(total=retries, backoff_factor=backoff_factor,
                               status_forcelist=[500, 502, 503, 504])
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)

        # Test connection
        self.connected = self._test_connection()

    def _build_url(self, endpoint: str) -> str:
        return f"{self.base_url}{self.api_prefix}/{endpoint.lstrip('/')}"

    def _request(self, method: str, url: str, **kwargs) -> requests.Response:
        self.logger.info(f"{method.upper()} {url}")
        response = self.session.request(method, url, timeout=self.timeout, **kwargs)
        self.logger.info(f"Status {response.status_code} for {url}")
        response.raise_for_status()
        return response

    def _get_paginated(self, endpoint: str, params: Optional[Dict] = None) -> pd.DataFrame:
        url = self._build_url(endpoint)
        results: List[Dict] = []
        while url:
            response = self._request('get', url, params=params)
            data = response.json()
            if isinstance(data, dict) and 'results' in data:
                results.extend(data['results'])
                url = data.get('next')
            else:
                if isinstance(data, list):
                    results.extend(data)
                else:
                    results.append(data)
                url = None
            params = None  # already in next url
        return pd.DataFrame(results)

    def _test_connection(self) -> bool:
        """Test the connection to the API."""
        try:
            url = f"{self.base_url}{self.api_prefix}/ping/"
            response = self.session.get(url, timeout=self.timeout)
            return response.status_code == 200
        except Exception as e:
            self.logger.error(f"Failed to connect to Django API: {e}")
            return False

    def get_trades(self, symbol=None, limit=100, offset=0) -> pd.DataFrame:
        """
        Get trades from the API.

        Args:
            symbol: Filter by symbol
            limit: Maximum number of trades to return
            offset: Offset for pagination

        Returns:
            DataFrame containing trade data
        """
        try:
            params = {
                'limit': limit,
                'offset': offset
            }
            if symbol:
                params['symbol'] = symbol

            return self._get_paginated('trades/', params=params)
        except Exception as e:
            self.logger.error(f"Error fetching trades: {e}")
            return pd.DataFrame()

    def get_ticks(self, symbol, limit=10000) -> pd.DataFrame:
        """
        Get tick data from the API.

        Args:
            symbol: The symbol to get ticks for
            limit: Maximum number of ticks to return

        Returns:
            DataFrame containing tick data
        """
        try:
            params = {
                'symbol': symbol,
                'limit': limit
            }

            return self._get_paginated('ticks/', params=params)
        except Exception as e:
            self.logger.error(f"Error fetching ticks for {symbol}: {e}")
            return pd.DataFrame()

    def get_bars(self, symbol, timeframe, limit=1000) -> pd.DataFrame:
        """
        Get bar data from the API.

        Args:
            symbol: The symbol to get bars for
            timeframe: The timeframe for the bars (e.g., '1m', '5m', '1h', '1d')
            limit: Maximum number of bars to return

        Returns:
            DataFrame containing bar data
        """
        try:
            params = {
                'symbol': symbol,
                'timeframe': timeframe,
                'limit': limit
            }

            return self._get_paginated('bars/', params=params)
        except Exception as e:
            self.logger.error(f"Error fetching bars for {symbol} {timeframe}: {e}")
            return pd.DataFrame()

    def send_market_order(self, symbol, volume, order_type, sl=0.0, tp=0.0, 
                          deviation=20, comment='', magic=0, type_filling='2') -> Dict:
        """
        Send a market order via the API.

        Args:
            symbol: The symbol to trade
            volume: The volume to trade
            order_type: The order type (0 for buy, 1 for sell)
            sl: Stop loss price
            tp: Take profit price
            deviation: Maximum price deviation
            comment: Order comment
            magic: Magic number
            type_filling: Order filling type

        Returns:
            Dictionary with the order result
        """
        try:
            data = {
                'symbol': symbol,
                'volume': volume,
                'order_type': order_type,
                'sl': sl,
                'tp': tp,
                'deviation': deviation,
                'comment': comment,
                'magic': magic,
                'type_filling': type_filling
            }

            response = self._request('post', self._build_url('send_market_order/'), json=data)
            return response.json()
        except Exception as e:
            self.logger.error(f"Error sending market order: {e}")
            return {'error': str(e)}

    def modify_sl_tp(self, ticket, sl=None, tp=None) -> Dict:
        """
        Modify stop loss and take profit for an existing order.

        Args:
            ticket: The position ticket
            sl: New stop loss price (optional)
            tp: New take profit price (optional)

        Returns:
            Dictionary with the modification result
        """
        try:
            data = {'ticket': ticket}
            if sl is not None:
                data['sl'] = sl
            if tp is not None:
                data['tp'] = tp

            response = self._request('post', self._build_url('modify_sl_tp/'), json=data)
            return response.json()
        except Exception as e:
            self.logger.error(f"Error modifying SL/TP: {e}")
            return {'error': str(e)}

    def get_symbols(self) -> List[str]:
        """Fetch available symbols from the API."""
        try:
            response = self._request('get', self._build_url('symbols/'))
            data = response.json()
            if isinstance(data, dict) and 'symbols' in data:
                return data['symbols']
            if isinstance(data, list):
                return data
            return []
        except Exception as e:
            self.logger.error(f"Error fetching symbols: {e}")
            return []

    def get_timeframes(self) -> List[str]:
        """Fetch available timeframes from the API."""
        try:
            response = self._request('get', self._build_url('timeframes/'))
            data = response.json()
            if isinstance(data, dict) and 'timeframes' in data:
                return data['timeframes']
            if isinstance(data, list):
                return data
            return []
        except Exception as e:
            self.logger.error(f"Error fetching timeframes: {e}")
            return []
