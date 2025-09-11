import os
import sys
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

# Ensure repo root on path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from services.pulse_api.main import app, PulseRuntime


def test_resources_released_on_shutdown():
    """Kafka producer and Redis connections should close on shutdown."""
    # Reset kernel singleton
    PulseRuntime._kernel = None

    kafka_mock = MagicMock()
    redis_mock = MagicMock()

    with patch('pulse_kernel.Producer', return_value=kafka_mock), \
         patch('pulse_kernel.redis.Redis') as RedisClass:
        RedisClass.from_url.return_value = redis_mock
        # Instantiate kernel with mocked resources
        PulseRuntime.kernel()

        # Trigger application shutdown by closing the TestClient context
        with TestClient(app) as client:
            client.get('/pulse/health')

    assert kafka_mock.flush.called
    assert kafka_mock.close.called
    assert redis_mock.close.called
