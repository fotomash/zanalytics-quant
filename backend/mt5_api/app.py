from fastapi import FastAPI
from fastapi.responses import JSONResponse
import os
import requests

app = FastAPI(title="MT5 HTTP Bridge (proxy with fallback)")


def _base_url() -> str:
    return os.getenv("MT5_API_URL") or os.getenv("MT5_API_BASE") or "http://mt5:5001"

def _stub_enabled() -> bool:
    val = os.getenv("MT5_API_STUB_FALLBACK", "1").strip().lower()
    return val in ("1", "true", "yes", "on")

def _stub_account_info():
    return {
        "login": "placeholder",
        "server": "mt5",
        "balance": 100000.00,
        "equity": 99850.00,
        "margin": 2500.00,
        "free_margin": 97350.00,
        "margin_level": 3994.0,
        "profit": -150.0,
        "leverage": 100,
        "currency": "USD",
        "source": "stub",
    }


@app.get("/health")
def health():
    # Report proxy health and underlying bridge reachability
    base = _base_url().rstrip("/")
    try:
        r = requests.get(f"{base}/health", timeout=2.0)
        if r.ok:
            return {"status": "ok", "bridge": r.json()}
        return {"status": "degraded", "bridge_http": r.status_code}
    except Exception as e:
        return {"status": "degraded", "error": str(e)}


@app.get("/account_info")
def account_info():
    base = _base_url().rstrip("/")
    try:
        r = requests.get(f"{base}/account_info", timeout=2.5)
        if r.ok:
            return JSONResponse(r.json())
        if _stub_enabled():
            return JSONResponse(_stub_account_info())
        return JSONResponse({"error": f"bridge_http_{r.status_code}"}, status_code=r.status_code)
    except Exception as e:
        if _stub_enabled():
            return JSONResponse(_stub_account_info())
        return JSONResponse({"error": str(e)}, status_code=502)


@app.get("/positions_get")
def positions_get():
    base = _base_url().rstrip("/")
    try:
        r = requests.get(f"{base}/positions_get", timeout=2.5)
        if r.ok:
            return JSONResponse(r.json())
        if _stub_enabled():
            return JSONResponse([])
        return JSONResponse([], status_code=r.status_code)
    except Exception:
        if _stub_enabled():
            return JSONResponse([])
        return JSONResponse([], status_code=502)
