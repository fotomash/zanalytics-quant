import pytest
from unittest.mock import MagicMock


class DiscordBot:
    """Simple Discord bot stub used for testing interactions.

    The bot supports two commands:
    - ``!store <key> <value>``: store value in Redis and memory API.
    - ``!recall <key>``: fetch value from Redis or fallback to memory API.
    """

    def __init__(self, redis_client, memory_api, ttl=60):
        self.redis = redis_client
        self.memory_api = memory_api
        self.ttl = ttl

    def handle_command(self, content: str) -> str:
        parts = content.strip().split(maxsplit=2)
        if not parts:
            raise ValueError("empty command")

        cmd = parts[0]
        if cmd == "!store" and len(parts) == 3:
            key, value = parts[1], parts[2]
            self.redis.set(key, value, ex=self.ttl)
            try:
                self.memory_api.store(key, value)
            except Exception:
                return "error"
            return "stored"
        if cmd == "!recall" and len(parts) == 2:
            key = parts[1]
            value = self.redis.get(key)
            if value is not None:
                return value
            try:
                value = self.memory_api.recall(key)
            except Exception:
                return "error"
            if value is None:
                return "not found"
            return value
        raise ValueError("unknown command")


def test_store_sets_redis_and_memory():
    redis = MagicMock()
    memory = MagicMock()
    bot = DiscordBot(redis, memory, ttl=30)

    result = bot.handle_command("!store foo bar")

    assert result == "stored"
    redis.set.assert_called_once_with("foo", "bar", ex=30)
    memory.store.assert_called_once_with("foo", "bar")


def test_recall_hits_redis_cache():
    redis = MagicMock()
    redis.get.return_value = "bar"
    memory = MagicMock()
    bot = DiscordBot(redis, memory)

    result = bot.handle_command("!recall foo")

    assert result == "bar"
    memory.recall.assert_not_called()


def test_recall_falls_back_to_memory():
    redis = MagicMock()
    redis.get.return_value = None
    memory = MagicMock()
    memory.recall.return_value = "bar"
    bot = DiscordBot(redis, memory)

    result = bot.handle_command("!recall foo")

    assert result == "bar"
    memory.recall.assert_called_once_with("foo")


def test_unknown_command_raises_value_error():
    bot = DiscordBot(MagicMock(), MagicMock())

    with pytest.raises(ValueError):
        bot.handle_command("!unknown")


def test_memory_store_error_returns_error():
    redis = MagicMock()
    memory = MagicMock()
    memory.store.side_effect = Exception("store fail")
    bot = DiscordBot(redis, memory)

    result = bot.handle_command("!store foo bar")

    assert result == "error"
