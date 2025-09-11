import asyncio

from services.llm.agent_manager import LLMAgentManager


class FakeAnalyzer:
    def __init__(self):
        self.last_prompt = ""

    async def analyze(self, prompt: str, threshold: float):
        self.last_prompt = prompt
        return True, "market shift"


class FakeMemory:
    async def get_agent_context(self, query: str):
        return ["past context"]


class FakeRedis:
    def __init__(self):
        self.published = []

    async def publish(self, channel: str, message: str):
        self.published.append((channel, message))


def test_publish_on_significant_shift():
    async def run():
        redis = FakeRedis()
        analyzer = FakeAnalyzer()
        memory = FakeMemory()
        manager = LLMAgentManager(redis, analyzer, memory, "risk query", interval=0)
        manager.start()
        await asyncio.sleep(0.01)
        await manager.stop()
        assert ("telegram-alerts", "market shift") in redis.published
        assert "past context" in analyzer.last_prompt
        assert "risk query" in analyzer.last_prompt

    asyncio.run(run())
