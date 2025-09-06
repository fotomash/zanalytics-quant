import requests


class SafeHTTP:
    """Minimal HTTP client with error handling."""

    def __init__(self, base: str, timeout: float = 2.0):
        self.base = base.rstrip("/")
        self.timeout = timeout

    def get(self, path: str):
        try:
            resp = requests.get(f"{self.base}{path}", timeout=self.timeout)
            resp.raise_for_status()
            try:
                return resp.json()
            except ValueError:
                return {"status_code": resp.status_code}
        except Exception as e:
            return {"error": str(e)}

