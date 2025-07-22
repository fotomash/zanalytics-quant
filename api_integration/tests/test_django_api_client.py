import os
import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from api_integration.django_api_client import DjangoAPIClient


def make_response(json_data):
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = json_data
    return resp


@patch('requests.sessions.Session.request')
def test_token_header(mock_request):
    mock_request.return_value = make_response({})

    client = DjangoAPIClient(base_url='http://test', token='abc')
    assert client.session.headers['Authorization'] == 'Token abc'

    client._request('get', client._build_url('trades/'))

    assert mock_request.call_count >= 2


@patch('requests.sessions.Session.request')
def test_pagination(mock_request):
    connection = make_response({})
    first = make_response({'results': [{'id': 1}], 'next': 'http://next/'})
    second = make_response({'results': [{'id': 2}], 'next': None})
    mock_request.side_effect = [connection, first, second]

    client = DjangoAPIClient(base_url='http://test', token='t')
    df = client.get_trades()

    assert len(df) == 2
    assert mock_request.call_count == 3  # connection + 2 pages

