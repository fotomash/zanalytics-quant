from redis import asyncio as redis_asyncio  # noqa: F401
import sys
from services.pulse_discord_bot import pulse_discord_bot as _impl

sys.modules[__name__] = _impl
