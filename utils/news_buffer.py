"""News Event Buffer for Volatility Protection"""

import requests
from datetime import datetime, timedelta
from typing import List, Dict


class NewsBuffer:
    """Buffer trading around high-impact news events"""

    def __init__(self, api_key: str = None):
        self.api_key = api_key
        self.buffer_minutes = 30  # Default buffer around news
        self.high_impact_events = []

    def fetch_calendar(self) -> List[Dict]:
        """Fetch economic calendar (implement with your preferred API)"""
        # Example: ForexFactory, Investing.com, or FRED API
        pass

    def is_news_buffer_active(self, timestamp: datetime) -> bool:
        """Check if we're in a news buffer period"""
        for event in self.high_impact_events:
            event_time = event['datetime']
            buffer_start = event_time - timedelta(minutes=self.buffer_minutes)
            buffer_end = event_time + timedelta(minutes=self.buffer_minutes)

            if buffer_start <= timestamp <= buffer_end:
                return True
        return False

    def get_buffer_reason(self, timestamp: datetime) -> str:
        """Get reason for news buffer"""
        for event in self.high_impact_events:
            event_time = event['datetime']
            buffer_start = event_time - timedelta(minutes=self.buffer_minutes)
            buffer_end = event_time + timedelta(minutes=self.buffer_minutes)

            if buffer_start <= timestamp <= buffer_end:
                return f"News buffer: {event['title']} at {event_time}"
        return ""
