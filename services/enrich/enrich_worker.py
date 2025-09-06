import asyncio
import json
import os


from components import confluence_engine, advanced_stoploss_lots_engine

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
STREAM_KEY = os.getenv("TICK_STREAM", "ticks:l1")
GROUP = "enrichers"
CONSUMER = os.getenv("CONSUMER", "enr-1")
PG_DSN = os.getenv("PG_DSN", "postgresql://pulse:pulse@localhost:5432/pulse")


def _ignore(exc: Exception) -> None:
    pass


async def ensure_group(r, stream: str, group: str) -> None:
    try:
        await r.xgroup_create(stream, group, id="$", mkstream=True)
    except Exception:
        pass


async def main() -> None:
    import aioredis
    import asyncpg
    r = await aioredis.from_url(REDIS_URL, encoding="utf-8", decode_responses=True)
    await ensure_group(r, STREAM_KEY, GROUP)
    pool = await asyncpg.create_pool(PG_DSN)

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
                    enriched = {}
                    try:
                        enriched["confluence"] = (
                            confluence_engine.compute_confluence_indicators_df(tick)
                        )
                        enriched["risk"] = (
                            advanced_stoploss_lots_engine.compute_risk_snapshot(tick)
                        )
                    except Exception as e:  # pragma: no cover - defensive
                        enriched["error"] = str(e)

                    await con.execute(
                        """
                        INSERT INTO ticks_enriched(symbol, ts, payload)
                        VALUES($1,$2,$3)
                        """,
                        tick["symbol"],
                        tick["ts"],
                        json.dumps(enriched),
                    )
                    await r.xack(STREAM_KEY, GROUP, msg_id)


if __name__ == "__main__":
    asyncio.run(main())
