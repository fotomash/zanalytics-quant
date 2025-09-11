# Pulse Telegram Bot

This service exposes a Telegram bot for interacting with the Pulse trading kernel.

## Environment Variables

- **`TELEGRAM_BOT_TOKEN`** – Bot token obtained from BotFather.
- **`TELEGRAM_CHAT_WHITELIST`** – Optional comma‑separated list of allowed chat IDs. When unset, all chats are accepted.
- **`PULSE_CONFIG`** – Path to the Pulse configuration file; defaults to `pulse_config.yaml`.

## Supported Commands

| Command | Description |
| --- | --- |
| `/help` | Show available commands. |
| `/status` | Display current risk and limit status. |
| `/score <SYMBOL>` | Get current confluence score for the symbol. |
| `/journal <TEXT>` | Append a note to the trading journal. |
| `/stats` | Show today’s trading statistics. |
| `/break <mins>` | Begin a voluntary cooling period. |

## Version

Built with [Aiogram 3.5.0](requirements.txt) and Python 3.11.

## Runtime Sharing

Both the bot and the REST API load the `PulseKernel` in their process. Sharing this
runtime means commands and API calls operate on the same risk metrics, journal
entries, and configuration, avoiding duplicated state or divergent trading logic.
