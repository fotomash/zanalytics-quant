#!/usr/bin/env python3
# File: tests/test_pulse_complete_integration.py

import pytest
import numpy as np
import pandas as pd
from unittest.mock import Mock, patch
import redis
import json

class TestPulseCompleteIntegration:
    """Complete integration test suite for Pulse with adaptive Wyckoff"""

    @pytest.fixture
    def sample_data(self):
        """Generate sample OHLCV data"""
        dates = pd.date_range('2024-01-01', periods=100, freq='1min')
        return pd.DataFrame({
            'open': np.random.randn(100).cumsum() + 100,
            'high': np.random.randn(100).cumsum() + 101,
            'low': np.random.randn(100).cumsum() + 99,
            'close': np.random.randn(100).cumsum() + 100,
            'volume': np.random.randint(1000, 10000, 100)
        }, index=dates)

    def test_adaptive_wyckoff_scoring(self, sample_data):
        """Test adaptive Wyckoff scorer with all features"""
        from components.wyckoff_adaptive import AdaptiveWyckoffCore

        scorer = AdaptiveWyckoffCore()
        result = scorer.score(sample_data)

        assert 'score' in result
        assert 'probs' in result
        assert 'reasons' in result
        assert 0 <= result['score'] <= 100
        assert len(result['probs']) == 4  # 4 Wyckoff phases

    def test_news_buffer_activation(self, sample_data):
        """Test news buffer properly masks volatile periods"""
        from components.wyckoff_scorer import WyckoffScorer

        # Inject high volatility spike
        sample_data.iloc[50:52, sample_data.columns.get_loc('volume')] *= 10

        scorer = WyckoffScorer()
        result = scorer.score(sample_data)

        assert 'news_mask' in result
        assert result['news_mask'][50] == True  # Should mask the spike
        assert result['score'] < 60  # Score should be clamped

    def test_mtf_conflict_resolution(self):
        """Test multi-timeframe conflict detection and resolution"""
        from components.wyckoff_mtf_resolver import MTFResolver

        resolver = MTFResolver()

        # Create conflicting signals
        signals = {
            '1m': {'phase': 'accumulation', 'confidence': 0.8},
            '5m': {'phase': 'distribution', 'confidence': 0.7},
            '15m': {'phase': 'distribution', 'confidence': 0.9}
        }

        resolved = resolver.resolve(signals)

        assert resolved['conflict'] == True
        assert resolved['penalty'] == 10  # Should apply penalty
        assert resolved['dominant_phase'] == 'distribution'  # Higher TF wins

    def test_risk_enforcer_with_news(self, sample_data):
        """Test risk enforcer respects news buffer"""
        from risk_enforcer import RiskEnforcer

        enforcer = RiskEnforcer()

        # High score but news event active
        signal = {
            'score': 85,
            'news_active': True,
            'reasons': ['Strong accumulation', 'News event detected']
        }

        allowed = enforcer.allow(signal)

        assert allowed == False  # Should block during news
        assert 'news_buffer_active' in enforcer.last_block_reason

    def test_api_endpoint_integration(self, sample_data):
        """Test Django API endpoint"""
        from django.test import Client
        import json

        client = Client()

        # Prepare request data
        bars = sample_data.reset_index().to_dict('records')
        for bar in bars:
            bar['ts'] = bar['index'].isoformat()
            del bar['index']

        response = client.post(
            '/api/pulse/wyckoff/score',
            json.dumps({'bars': bars}),
            content_type='application/json'
        )

        assert response.status_code == 200
        data = response.json()
        assert 'score' in data
        assert 'probs' in data
        assert 'reasons' in data

    def test_redis_streaming(self, sample_data):
        """Test Redis stream publishing"""
        r = redis.Redis(host='localhost', port=6379, decode_responses=True)

        from services.tick_to_bar import TickToBarService

        service = TickToBarService()

        # Simulate tick data
        for i in range(100):
            tick = {
                'symbol': 'EURUSD',
                'bid': 1.0850 + np.random.randn() * 0.0001,
                'ask': 1.0851 + np.random.randn() * 0.0001,
                'volume': np.random.randint(100, 1000)
            }
            service.process_tick(tick)

        # Check stream has data
        messages = r.xread({'stream:pulse:signals:EURUSD': 0}, count=10)
        assert len(messages) > 0

    def test_prometheus_metrics(self):
        """Test Prometheus metrics are properly exposed"""
        from utils.metrics import (
            WYCKOFF_PHASE_CONFIDENCE,
            WYCKOFF_CONFLICTS_TOTAL,
            WYCKOFF_EVENTS_CONFIRMED_TOTAL
        )

        # Simulate metric updates
        WYCKOFF_PHASE_CONFIDENCE.labels(symbol='EURUSD', timeframe='1m').set(0.85)
        WYCKOFF_CONFLICTS_TOTAL.labels(symbol='EURUSD').inc()
        WYCKOFF_EVENTS_CONFIRMED_TOTAL.labels(symbol='EURUSD', event_type='Spring').inc()

        # Verify metrics are registered
        from prometheus_client import REGISTRY

        metrics = [m.name for m in REGISTRY.collect()]
        assert 'wyckoff_phase_confidence' in str(metrics)
        assert 'wyckoff_conflicts_total' in str(metrics)

    def test_end_to_end_signal_flow(self, sample_data):
        """Test complete signal flow from data to decision"""
        from pulse_kernel import PulseKernel

        kernel = PulseKernel()

        # Process frame
        result = kernel.process_frame({
            'symbol': 'EURUSD',
            'timeframe': '1m',
            'data': sample_data
        })

        # Verify complete response
        assert 'action' in result  # BUY/SELL/HOLD
        assert 'confidence' in result
        assert 'risk_approved' in result
        assert 'reasons' in result
        assert 'metrics' in result

        # Verify metrics logged
        assert result['metrics']['processing_time_ms'] < 200
        assert result['metrics']['components_checked'] == ['smc', 'wyckoff', 'technical']

if __name__ == '__main__':
    pytest.main([__file__, '-v'])
