import os
import asyncio
import json
import logging
from typing import Iterable, Optional, Protocol, Tuple

from redis.asyncio import Redis


logger = logging.getLogger(__name__)


class AgentMemoryInterface(Protocol):
    async def get_agent_context(self, query: str) -> Iterable[str]:
        ...


class MarketNarrativeAnalyzer(Protocol):
    async def analyze(self, prompt: str, threshold: float) -> Tuple[bool, str]:
        ...


class LLMAgentManager:
    """Periodically analyze market narrative and publish significant shifts."""

    def __init__(
        self,
        redis_client: Redis,
        analyzer: MarketNarrativeAnalyzer,
        memory_interface: AgentMemoryInterface,
        query: str,
        interval: Optional[int] = None,
        threshold: Optional[float] = None,
    ) -> None:
        self.redis = redis_client
        self.analyzer = analyzer
        self.memory = memory_interface
        self.query = query
        self.interval = interval or int(os.getenv("LLM_AGENT_INTERVAL", "3600"))
        self.threshold = threshold or float(
            os.getenv("LLM_AGENT_SIGNIFICANCE_THRESHOLD", "0.5")
        )
        self._task: Optional[asyncio.Task] = None
        self._stopping = False

    async def _run_cycle(self) -> None:
        try:
            memories = await self.memory.get_agent_context(self.query)
            formatted_memory = "\n".join(f"- {m}" for m in memories)
            prompt = (
                "You are a Market Narrative Analyzer.\n\n"
                "**Relevant Historical Context (from memory):**\n"
                f"{formatted_memory}\n\n"
                "**Current Deterministic Analysis:**\n"
                "- [Contents of the latest UnifiedAnalysisPayload]\n\n"
                "**User Query:**\n"
                f"- \"{self.query}\"\n\n"
                "Please provide your analysis."
            )
            is_significant, summary = await self.analyzer.analyze(
                prompt, self.threshold
            )
            if is_significant and summary:
                await self.redis.publish("telegram-alerts", summary)
        except json.JSONDecodeError:
            logger.exception("JSON decoding error during agent cycle")
        except Exception:
            logger.exception("Unexpected error during agent cycle")

    async def _run(self) -> None:
        try:
            while not self._stopping:
                try:
                    await self._run_cycle()
                except Exception:
                    logger.exception("Agent cycle failed")
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
