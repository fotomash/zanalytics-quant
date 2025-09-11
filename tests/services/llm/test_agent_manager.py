import asyncio

from services.llm.agent_manager import LLMAgentManager


class FakeAnalyzer:
    async def analyze(self, threshold: float):
        return True, "market shift"


class FakeRedis:
    def __init__(self):
        self.published = []

    async def publish(self, channel: str, message: str):
        self.published.append((channel, message))


def test_publish_on_significant_shift():
    async def run():
        redis = FakeRedis()
        analyzer = FakeAnalyzer()
        manager = LLMAgentManager(redis, analyzer, interval=0)
        manager.start()
        await asyncio.sleep(0.01)
        await manager.stop()
        assert ("telegram-alerts", "market shift") in redis.published

    asyncio.run(run())
