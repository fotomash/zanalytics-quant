tom@mm20 zanalytics-quant % docker compose logs django
django  | 
django  | 166 static files copied to '/app/backend/django/staticfiles', 476 post-processed.
django  | [2025-09-09 14:58:22 +0000] [7] [INFO] Starting gunicorn 23.0.0
django  | [2025-09-09 14:58:22 +0000] [7] [INFO] Listening at: http://0.0.0.0:8000 (7)
django  | [2025-09-09 14:58:22 +0000] [7] [INFO] Using worker: sync
django  | [2025-09-09 14:58:22 +0000] [14] [INFO] Booting worker with pid: 14
django  | [2025-09-09 14:58:22 +0000] [15] [INFO] Booting worker with pid: 15
django  | [2025-09-09 14:58:22 +0000] [16] [INFO] Booting worker with pid: 16
django  | Not Found: /api/v1/positions/live
django  | Bad Gateway: /history_deals_get
django  | Bad Gateway: /history_orders_get
django  | Bad Request: /api/pulse/score/peek
django  | Not Found: /api/v1/trades/summary/
django  | Bad Gateway: /history_deals_get
django  | Bad Gateway: /history_orders_get
django  | Bad Request: /api/pulse/score/peek
django  | Not Found: /api/v1/trades/summary/
django  | Bad Gateway: /history_deals_get
django  | Bad Gateway: /history_orders_get
django  | Bad Request: /api/pulse/score/peek
django  | Not Found: /api/v1/trades/summary/
django  | Exception fetching bars for EURUSD H4: HTTPConnectionPool(host='mt5', port=5001): Max retries exceeded with url: /bars/EURUSD/H4?limit=300 (Caused by NewConnectionError('<urllib3.connection.HTTPConnection object at 0x7f03710aad50>: Failed to establish a new connection: [Errno 111] Connection refused'))
django  | Traceback (most recent call last):
django  |   File "/usr/local/lib/python3.11/site-packages/urllib3/connection.py", line 199, in _new_conn
django  |     sock = connection.create_connection(
django  |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
django  |   File "/usr/local/lib/python3.11/site-packages/urllib3/util/connection.py", line 85, in create_connection
django  |     raise err
django  |   File "/usr/local/lib/python3.11/site-packages/urllib3/util/connection.py", line 73, in create_connection
django  |     sock.connect(sa)
django  | ConnectionRefusedError: [Errno 111] Connection refused
django  | 
django  | The above exception was the direct cause of the following exception:
django  | 
django  | Traceback (most recent call last):
django  |   File "/usr/local/lib/python3.11/site-packages/urllib3/connectionpool.py", line 789, in urlopen
django  |     response = self._make_request(
django  |                ^^^^^^^^^^^^^^^^^^^
django  |   File "/usr/local/lib/python3.11/site-packages/urllib3/connectionpool.py", line 495, in _make_request
django  |     conn.request(
django  |   File "/usr/local/lib/python3.11/site-packages/urllib3/connection.py", line 441, in request
django  |     self.endheaders()
django  |   File "/usr/local/lib/python3.11/http/client.py", line 1298, in endheaders
django  |     self._send_output(message_body, encode_chunked=encode_chunked)
django  |   File "/usr/local/lib/python3.11/http/client.py", line 1058, in _send_output
django  |     self.send(msg)
django  |   File "/usr/local/lib/python3.11/http/client.py", line 996, in send
django  |     self.connect()
django  |   File "/usr/local/lib/python3.11/site-packages/urllib3/connection.py", line 279, in connect
django  |     self.sock = self._new_conn()
django  |                 ^^^^^^^^^^^^^^^^
django  |   File "/usr/local/lib/python3.11/site-packages/urllib3/connection.py", line 214, in _new_conn
django  |     raise NewConnectionError(
django  | urllib3.exceptions.NewConnectionError: <urllib3.connection.HTTPConnection object at 0x7f03710aad50>: Failed to establish a new connection: [Errno 111] Connection refused
django  | 
django  | The above exception was the direct cause of the following exception:
django  | 
django  | Traceback (most recent call last):
django  |   File "/usr/local/lib/python3.11/site-packages/requests/adapters.py", line 667, in send
django  |     resp = conn.urlopen(
django  |            ^^^^^^^^^^^^^
django  |   File "/usr/local/lib/python3.11/site-packages/urllib3/connectionpool.py", line 843, in urlopen
django  |     retries = retries.increment(
django  |               ^^^^^^^^^^^^^^^^^^
django  |   File "/usr/local/lib/python3.11/site-packages/urllib3/util/retry.py", line 519, in increment
django  |     raise MaxRetryError(_pool, url, reason) from reason  # type: ignore[arg-type]
django  |     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
django  | urllib3.exceptions.MaxRetryError: HTTPConnectionPool(host='mt5', port=5001): Max retries exceeded with url: /bars/EURUSD/H4?limit=300 (Caused by NewConnectionError('<urllib3.connection.HTTPConnection object at 0x7f03710aad50>: Failed to establish a new connection: [Errno 111] Connection refused'))
django  | 
django  | During handling of the above exception, another exception occurred:
django  | 
django  | Traceback (most recent call last):
django  |   File "/app/backend/django/app/utils/api/data.py", line 99, in fetch_bars
django  |     response = requests.get(url, params=params)
django  |                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
django  |   File "/usr/local/lib/python3.11/site-packages/requests/api.py", line 73, in get
django  |     return request("get", url, params=params, **kwargs)
django  |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
django  |   File "/usr/local/lib/python3.11/site-packages/requests/api.py", line 59, in request
django  |     return session.request(method=method, url=url, **kwargs)
django  |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
django  |   File "/usr/local/lib/python3.11/site-packages/requests/sessions.py", line 589, in request
django  |     resp = self.send(prep, **send_kwargs)
django  |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
django  |   File "/usr/local/lib/python3.11/site-packages/requests/sessions.py", line 703, in send
django  |     r = adapter.send(request, **kwargs)
django  |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
django  |   File "/usr/local/lib/python3.11/site-packages/requests/adapters.py", line 700, in send
django  |     raise ConnectionError(e, request=request)
django  | requests.exceptions.ConnectionError: HTTPConnectionPool(host='mt5', port=5001): Max retries exceeded with url: /bars/EURUSD/H4?limit=300 (Caused by NewConnectionError('<urllib3.connection.HTTPConnection object at 0x7f03710aad50>: Failed to establish a new connection: [Errno 111] Connection refused'))
django  | 
django  | Exception fetching bars for EURUSD H1: HTTPConnectionPool(host='mt5', port=5001): Max retries exceeded with url: /bars/EURUSD/H1?limit=600 (Caused by NewConnectionError('<urllib3.connection.HTTPConnection object at 0x7f0370e72a10>: Failed to establish a new connection: [Errno 111] Connection refused'))
django  | Traceback (most recent call last):
django  |   File "/usr/local/lib/python3.11/site-packages/urllib3/connection.py", line 199, in _new_conn
django  |     sock = connection.create_connection(
django  |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
django  |   File "/usr/local/lib/python3.11/site-packages/urllib3/util/connection.py", line 85, in create_connection
django  |     raise err
django  |   File "/usr/local/lib/python3.11/site-packages/urllib3/util/connection.py", line 73, in create_connection
django  |     sock.connect(sa)
django  | ConnectionRefusedError: [Errno 111] Connection refused
django  | 
django  | The above exception was the direct cause of the following exception:
django  | 
django  | Traceback (most recent call last):
django  |   File "/usr/local/lib/python3.11/site-packages/urllib3/connectionpool.py", line 789, in urlopen
django  |     response = self._make_request(
django  |                ^^^^^^^^^^^^^^^^^^^
django  |   File "/usr/local/lib/python3.11/site-packages/urllib3/connectionpool.py", line 495, in _make_request
django  |     conn.request(
django  |   File "/usr/local/lib/python3.11/site-packages/urllib3/connection.py", line 441, in request
django  |     self.endheaders()
django  |   File "/usr/local/lib/python3.11/http/client.py", line 1298, in endheaders
django  |     self._send_output(message_body, encode_chunked=encode_chunked)
django  |   File "/usr/local/lib/python3.11/http/client.py", line 1058, in _send_output
django  |     self.send(msg)
django  |   File "/usr/local/lib/python3.11/http/client.py", line 996, in send
django  |     self.connect()
django  |   File "/usr/local/lib/python3.11/site-packages/urllib3/connection.py", line 279, in connect
django  |     self.sock = self._new_conn()
django  |                 ^^^^^^^^^^^^^^^^
django  |   File "/usr/local/lib/python3.11/site-packages/urllib3/connection.py", line 214, in _new_conn
django  |     raise NewConnectionError(
django  | urllib3.exceptions.NewConnectionError: <urllib3.connection.HTTPConnection object at 0x7f0370e72a10>: Failed to establish a new connection: [Errno 111] Connection refused
django  | 
django  | The above exception was the direct cause of the following exception:
django  | 
django  | Traceback (most recent call last):
django  |   File "/usr/local/lib/python3.11/site-packages/requests/adapters.py", line 667, in send
django  |     resp = conn.urlopen(
django  |            ^^^^^^^^^^^^^
django  |   File "/usr/local/lib/python3.11/site-packages/urllib3/connectionpool.py", line 843, in urlopen
django  |     retries = retries.increment(
django  |               ^^^^^^^^^^^^^^^^^^
django  |   File "/usr/local/lib/python3.11/site-packages/urllib3/util/retry.py", line 519, in increment
django  |     raise MaxRetryError(_pool, url, reason) from reason  # type: ignore[arg-type]
django  |     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
django  | urllib3.exceptions.MaxRetryError: HTTPConnectionPool(host='mt5', port=5001): Max retries exceeded with url: /bars/EURUSD/H1?limit=600 (Caused by NewConnectionError('<urllib3.connection.HTTPConnection object at 0x7f0370e72a10>: Failed to establish a new connection: [Errno 111] Connection refused'))
django  | 
django  | During handling of the above exception, another exception occurred:
django  | 
django  | Traceback (most recent call last):
django  |   File "/app/backend/django/app/utils/api/data.py", line 99, in fetch_bars
django  |     response = requests.get(url, params=params)
django  |                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
django  |   File "/usr/local/lib/python3.11/site-packages/requests/api.py", line 73, in get
django  |     return request("get", url, params=params, **kwargs)
django  |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
django  |   File "/usr/local/lib/python3.11/site-packages/requests/api.py", line 59, in request
django  |     return session.request(method=method, url=url, **kwargs)
django  |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
django  |   File "/usr/local/lib/python3.11/site-packages/requests/sessions.py", line 589, in request
django  |     resp = self.send(prep, **send_kwargs)
django  |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
django  |   File "/usr/local/lib/python3.11/site-packages/requests/sessions.py", line 703, in send
django  |     r = adapter.send(request, **kwargs)
django  |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
django  |   File "/usr/local/lib/python3.11/site-packages/requests/adapters.py", line 700, in send
django  |     raise ConnectionError(e, request=request)
django  | requests.exceptions.ConnectionError: HTTPConnectionPool(host='mt5', port=5001): Max retries exceeded with url: /bars/EURUSD/H1?limit=600 (Caused by NewConnectionError('<urllib3.connection.HTTPConnection object at 0x7f0370e72a10>: Failed to establish a new connection: [Errno 111] Connection refused'))
django  | 
django  | Exception fetching bars for EURUSD M15: HTTPConnectionPool(host='mt5', port=5001): Max retries exceeded with url: /bars/EURUSD/M15?limit=800 (Caused by NewConnectionError('<urllib3.connection.HTTPConnection object at 0x7f0370e936d0>: Failed to establish a new connection: [Errno 111] Connection refused'))
django  | Traceback (most recent call last):
django  |   File "/usr/local/lib/python3.11/site-packages/urllib3/connection.py", line 199, in _new_conn
django  |     sock = connection.create_connection(
django  |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
django  |   File "/usr/local/lib/python3.11/site-packages/urllib3/util/connection.py", line 85, in create_connection
django  |     raise err
django  |   File "/usr/local/lib/python3.11/site-packages/urllib3/util/connection.py", line 73, in create_connection
django  |     sock.connect(sa)
django  | ConnectionRefusedError: [Errno 111] Connection refused
django  | 
django  | The above exception was the direct cause of the following exception:
django  | 
django  | Traceback (most recent call last):
django  |   File "/usr/local/lib/python3.11/site-packages/urllib3/connectionpool.py", line 789, in urlopen
django  |     response = self._make_request(
django  |                ^^^^^^^^^^^^^^^^^^^
django  |   File "/usr/local/lib/python3.11/site-packages/urllib3/connectionpool.py", line 495, in _make_request
django  |     conn.request(
django  |   File "/usr/local/lib/python3.11/site-packages/urllib3/connection.py", line 441, in request
django  |     self.endheaders()
django  |   File "/usr/local/lib/python3.11/http/client.py", line 1298, in endheaders
django  |     self._send_output(message_body, encode_chunked=encode_chunked)
django  |   File "/usr/local/lib/python3.11/http/client.py", line 1058, in _send_output
django  |     self.send(msg)
django  |   File "/usr/local/lib/python3.11/http/client.py", line 996, in send
django  |     self.connect()
django  |   File "/usr/local/lib/python3.11/site-packages/urllib3/connection.py", line 279, in connect
django  |     self.sock = self._new_conn()
django  |                 ^^^^^^^^^^^^^^^^
django  |   File "/usr/local/lib/python3.11/site-packages/urllib3/connection.py", line 214, in _new_conn
django  |     raise NewConnectionError(
django  | urllib3.exceptions.NewConnectionError: <urllib3.connection.HTTPConnection object at 0x7f0370e936d0>: Failed to establish a new connection: [Errno 111] Connection refused
django  | 
django  | The above exception was the direct cause of the following exception:
django  | 
django  | Traceback (most recent call last):
django  |   File "/usr/local/lib/python3.11/site-packages/requests/adapters.py", line 667, in send
django  |     resp = conn.urlopen(
django  |            ^^^^^^^^^^^^^
django  |   File "/usr/local/lib/python3.11/site-packages/urllib3/connectionpool.py", line 843, in urlopen
django  |     retries = retries.increment(
django  |               ^^^^^^^^^^^^^^^^^^
django  |   File "/usr/local/lib/python3.11/site-packages/urllib3/util/retry.py", line 519, in increment
django  |     raise MaxRetryError(_pool, url, reason) from reason  # type: ignore[arg-type]
django  |     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
django  | urllib3.exceptions.MaxRetryError: HTTPConnectionPool(host='mt5', port=5001): Max retries exceeded with url: /bars/EURUSD/M15?limit=800 (Caused by NewConnectionError('<urllib3.connection.HTTPConnection object at 0x7f0370e936d0>: Failed to establish a new connection: [Errno 111] Connection refused'))
django  | 
django  | During handling of the above exception, another exception occurred:
django  | 
django  | Traceback (most recent call last):
django  |   File "/app/backend/django/app/utils/api/data.py", line 99, in fetch_bars
django  |     response = requests.get(url, params=params)
django  |                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
django  |   File "/usr/local/lib/python3.11/site-packages/requests/api.py", line 73, in get
django  |     return request("get", url, params=params, **kwargs)
django  |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
django  |   File "/usr/local/lib/python3.11/site-packages/requests/api.py", line 59, in request
django  |     return session.request(method=method, url=url, **kwargs)
django  |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
django  |   File "/usr/local/lib/python3.11/site-packages/requests/sessions.py", line 589, in request
django  |     resp = self.send(prep, **send_kwargs)
django  |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
django  |   File "/usr/local/lib/python3.11/site-packages/requests/sessions.py", line 703, in send
django  |     r = adapter.send(request, **kwargs)
django  |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
django  |   File "/usr/local/lib/python3.11/site-packages/requests/adapters.py", line 700, in send
django  |     raise ConnectionError(e, request=request)
django  | requests.exceptions.ConnectionError: HTTPConnectionPool(host='mt5', port=5001): Max retries exceeded with url: /bars/EURUSD/M15?limit=800 (Caused by NewConnectionError('<urllib3.connection.HTTPConnection object at 0x7f0370e936d0>: Failed to establish a new connection: [Errno 111] Connection refused'))
django  | 
django  | Bad Gateway: /history_deals_get
django  | Bad Gateway: /history_orders_get
django  | Bad Request: /api/pulse/score/peek