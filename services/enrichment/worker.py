"""Streaming enrichment worker.

Consumes tick data from a Redis stream, enriches each tick, and
persists the result to Postgres.
"""

import asyncio
import json
import os

from utils.analysis_engines import build_unified_analysis

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
VERSION_PREFIX = os.getenv("STREAM_VERSION_PREFIX", "v2")
STREAM_KEY = os.getenv("TICK_STREAM", f"{VERSION_PREFIX}:ticks:l1")
GROUP = "enrichers"
CONSUMER = os.getenv("CONSUMER", "enr-1")


async def ensure_group(r, stream: str, group: str) -> None:
    try:
        await r.xgroup_create(stream, group, id="$", mkstream=True)
    except Exception:
        pass


async def main() -> None:
    pg_dsn = os.getenv("PG_DSN")
    if not pg_dsn:
        raise RuntimeError(
            "PG_DSN must be set via environment variable or configuration file"
        )

    from redis import asyncio as redis_asyncio
    import asyncpg

    r = await redis_asyncio.from_url(
        REDIS_URL, encoding="utf-8", decode_responses=True
    )
    await ensure_group(r, STREAM_KEY, GROUP)
    pool = await asyncpg.create_pool(pg_dsn)

    while True:
        msgs = await r.xreadgroup(
            GROUP, CONSUMER, streams={STREAM_KEY: ">"}, count=200, block=1000
        )
        if not msgs:
            continue
        async with pool.acquire() as con:
            for _, entries in msgs:
                for msg_id, fields in entries:
                    tick = json.loads(fields["j"])
                    try:
                        payload = build_unified_analysis(tick)
                        enriched_json = payload.model_dump(exclude_none=False)
                    except Exception as e:  # pragma: no cover - defensive
                        enriched_json = {"error": str(e)}

                    await con.execute(
                        """
                        INSERT INTO ticks_enriched(symbol, ts, payload)
                        VALUES($1,$2,$3)
                        """,
                        tick["symbol"],
                        tick["ts"],
                        json.dumps(enriched_json),
                    )
                    await r.xack(STREAM_KEY, GROUP, msg_id)


if __name__ == "__main__":
    asyncio.run(main())

