"""Compatibility wrapper for the Pulse Discord bot.

This module preserves the legacy ``pulse_discord_bot`` entry point while
redirecting all imports to the canonical implementation at
``services.pulse_bot.bot``.
"""

import sys

from services.pulse_bot import bot as _impl

sys.modules[__name__] = _impl
