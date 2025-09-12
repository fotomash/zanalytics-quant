import os
from redis import Redis


def get_redis_connection() -> Redis:
    """Return a Redis connection using ``REDIS_URL`` configuration.

    The connection string is read from the ``REDIS_URL`` environment
    variable and defaults to ``redis://localhost:6379/0``. Responses are
    decoded as UTF-8 strings.
    """
    url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    return Redis.from_url(url, decode_responses=True)
