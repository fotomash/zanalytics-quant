import os
import httpx

BASE = os.getenv("PULSE_API_URL", "http://localhost:8080")


async def score(symbol: str, tf: str = "M15"):
    async with httpx.AsyncClient(timeout=10) as c:
        r = await c.post(f"{BASE}/pulse/score", json={"symbol": symbol, "tf": tf})
        r.raise_for_status()
        return r.json()


async def risk(size: float, score: int):
    async with httpx.AsyncClient(timeout=10) as c:
        r = await c.post(f"{BASE}/pulse/risk", json={"size": size, "score": score})
        r.raise_for_status()
        return r.json()


async def journal(entry: dict):
    async with httpx.AsyncClient(timeout=10) as c:
        r = await c.post(f"{BASE}/pulse/journal", json=entry)
        r.raise_for_status()
        return r.json()
