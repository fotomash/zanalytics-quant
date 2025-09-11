"""Pydantic models for the MCP server."""

from typing import Literal

from .schemas import StrategyPayloadV1

from pydantic import BaseModel


# Enumerated action names accepted by the Actions Bus.
WHISPER_SUGGEST = "whisper_suggest"
SESSION_BOOT = "session_boot"
TRADES_RECENT = "trades_recent"
TRADES_HISTORY_MT5 = "trades_history_mt5"
ACCOUNT_POSITIONS = "account_positions"

ActionType = Literal[
    WHISPER_SUGGEST,
    SESSION_BOOT,
    TRADES_RECENT,
    TRADES_HISTORY_MT5,
    ACCOUNT_POSITIONS,
]


class ActionsQuery(BaseModel):
    """Request model for ``POST /api/v1/actions/query``.

    Attributes:
        type: Enumerated action name to execute.
        approve: Skip UI confirmations when ``True``.
        payload: Optional data required by the action.
    """

    type: ActionType
    approve: bool = False
    payload: StrategyPayloadV1 | dict | None = None


__all__ = [
    "ACCOUNT_POSITIONS",
    "ActionType",
    "ActionsQuery",
    "SESSION_BOOT",
    "TRADES_HISTORY_MT5",
    "TRADES_RECENT",
    "WHISPER_SUGGEST",
]
