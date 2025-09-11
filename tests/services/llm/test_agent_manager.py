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


class FlakyAnalyzer:
    def __init__(self):
        self.calls = 0

    async def analyze(self, prompt: str, threshold: float):
        self.calls += 1
        if self.calls == 1:
            raise RuntimeError("boom")
        return True, "market shift"


def test_analyzer_exception_does_not_stop_loop():
    async def run():
        redis = FakeRedis()
        analyzer = FlakyAnalyzer()
        memory = FakeMemory()
        manager = LLMAgentManager(redis, analyzer, memory, "risk query", interval=0.01)
        manager.start()
        await asyncio.sleep(0.05)
        await manager.stop()
        assert analyzer.calls >= 2
        assert ("telegram-alerts", "market shift") in redis.published

    asyncio.run(run())
