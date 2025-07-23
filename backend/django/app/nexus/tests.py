from rest_framework.test import APIClient, APITestCase
from rest_framework.response import Response
from unittest.mock import patch


class TickBarAPITests(APITestCase):
    def setUp(self):
        self.client = APIClient()

    @patch('app.nexus.views.TickViewSet.list')
    def test_get_ticks(self, mock_list):
        sample = [{'symbol': 'EURUSD', 'bid': 1.1}, {'symbol': 'EURUSD', 'bid': 1.11}]
        mock_list.return_value = Response(sample)
        response = self.client.get('/api/v1/ticks/?symbol=EURUSD')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), sample)

    @patch('app.nexus.views.BarViewSet.list')
    def test_get_bars(self, mock_list):
        sample = [
            {'symbol': 'EURUSD', 'timeframe': 'M1', 'open': 1.0},
            {'symbol': 'EURUSD', 'timeframe': 'M1', 'open': 1.1},
        ]
        mock_list.return_value = Response(sample)
        response = self.client.get('/api/v1/bars/?symbol=EURUSD&timeframe=M1')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), sample)

    @patch("app.nexus.views.SymbolListView.get")
    def test_get_symbols(self, mock_get):
        sample = {"symbols": ["EURUSD", "GBPUSD"]}
        mock_get.return_value = Response(sample)
        response = self.client.get("/api/v1/symbols/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), sample)

    @patch("app.nexus.views.TimeframeListView.get")
    def test_get_timeframes(self, mock_get):
        sample = {"timeframes": ["M1", "H1"]}
        mock_get.return_value = Response(sample)
        response = self.client.get("/api/v1/timeframes/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), sample)

    def test_ping(self):
        response = self.client.get("/api/v1/ping/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})
