import os
import asyncio
from typing import Protocol, Tuple, Optional

from redis.asyncio import Redis


class MarketNarrativeAnalyzer(Protocol):
    async def analyze(self, threshold: float) -> Tuple[bool, str]:
        ...


class LLMAgentManager:
    """Periodically analyze market narrative and publish significant shifts."""

    def __init__(
        self,
        redis_client: Redis,
        analyzer: MarketNarrativeAnalyzer,
        interval: Optional[int] = None,
        threshold: Optional[float] = None,
    ) -> None:
        self.redis = redis_client
        self.analyzer = analyzer
        self.interval = interval or int(os.getenv("LLM_AGENT_INTERVAL", "3600"))
        self.threshold = threshold or float(
            os.getenv("LLM_AGENT_SIGNIFICANCE_THRESHOLD", "0.5")
        )
        self._task: Optional[asyncio.Task] = None
        self._stopping = False

    async def _run_cycle(self) -> None:
        is_significant, summary = await self.analyzer.analyze(self.threshold)
        if is_significant and summary:
            await self.redis.publish("telegram-alerts", summary)

    async def _run(self) -> None:
        try:
            while not self._stopping:
                await self._run_cycle()
                await asyncio.sleep(self.interval)
        except asyncio.CancelledError:
            pass

    def start(self) -> None:
        if not self._task:
            self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        if self._task:
            self._stopping = True
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
            self._stopping = False
