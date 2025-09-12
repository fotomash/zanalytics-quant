import asyncio
import hashlib
import json
import os
import time
import logging
from datetime import datetime, timezone



REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
PG_DSN = os.getenv("PG_DSN", "postgresql://pulse:pulse@localhost:5432/pulse")
VERSION_PREFIX = os.getenv("STREAM_VERSION_PREFIX", "v2")
STREAM_KEY = os.getenv("TICK_STREAM", f"{VERSION_PREFIX}:ticks:l1")
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "1000"))
FLUSH_MS = int(os.getenv("FLUSH_MS", "250"))

logger = logging.getLogger(__name__)


class TickBuffer:
    def __init__(self, batch: int = BATCH_SIZE) -> None:
        self.batch = batch
        self.buf: list[dict] = []
        self.hash_seen: set[str] = set()

    def add(self, tick: dict) -> bool:
        raw = f"{tick['symbol']}|{tick['ts']}|{tick['bid']}|{tick['ask']}".encode()
        h = hashlib.md5(raw).hexdigest()
        if h in self.hash_seen:
            return False
        self.hash_seen.add(h)
        self.buf.append({**tick, "hash": h})
        return len(self.buf) >= self.batch

    def flush(self) -> list[dict]:
        data, self.buf = self.buf, []
        self.hash_seen.clear()
        return data


async def insert_batch(conn, batch: list[dict], max_retries: int = 3, base_delay: float = 0.1) -> None:
    delay = base_delay
    for attempt in range(1, max_retries + 1):
        try:
            await conn.executemany(
                """
                INSERT INTO ticks_l1(symbol, ts, bid, ask, volume, hash)
                VALUES($1,$2,$3,$4,$5,$6)
                ON CONFLICT (hash) DO NOTHING;
                """,
                [
                    (
                        t["symbol"],
                        t["ts"],
                        t["bid"],
                        t["ask"],
                        t.get("volume", 0),
                        t["hash"],
                    )
                    for t in batch
                ],
            )
            return
        except Exception as exc:  # pragma: no cover - defensive
            rollback = getattr(conn, "rollback", None)
            if rollback is not None:
                await rollback()
            else:
                await conn.execute("ROLLBACK")
            logger.exception("Batch insert failed on attempt %s", attempt, exc_info=exc)
            if attempt >= max_retries:
                raise
            await asyncio.sleep(delay)
            delay *= 2


async def main() -> None:
    import redis.asyncio as redis
    import asyncpg
    from adapters.mt5_client import MT5AsyncClient  # local import to avoid hard dep
    r = await redis.from_url(REDIS_URL, encoding="utf-8", decode_responses=True)
    pool = await asyncpg.create_pool(PG_DSN, min_size=1, max_size=5)
    mt5 = MT5AsyncClient(auto_reconnect=True)  # implement reconnect with backoff

    buf = TickBuffer()
    last_flush = time.monotonic()

    async for tick in mt5.stream_ticks():  # yields dict: {symbol, bid, ask, ts, volume}
        tick["ts"] = tick.get("ts") or datetime.now(timezone.utc).isoformat()
        # 1) push to Redis stream (for live consumers)
        await r.xadd(
            STREAM_KEY, {"j": json.dumps(tick)}, maxlen=100_000, approximate=True
        )
        # 2) accumulate & dedupe for DB batch
        if buf.add(tick) or (time.monotonic() - last_flush) * 1000 >= FLUSH_MS:
            batch = buf.flush()
            last_flush = time.monotonic()
            if batch:
                async with pool.acquire() as con:
                    await insert_batch(con, batch)


if __name__ == "__main__":
    asyncio.run(main())
