# Pulse Discord Bot

This service exposes a Discord bot for interacting with the Pulse trading kernel.

## Environment Variables

- **`DISCORD_BOT_TOKEN`** – Bot token obtained from the Discord developer portal.
- **`DISCORD_CHANNEL_WHITELIST`** – Optional comma‑separated list of allowed channel IDs. When unset, all channels are accepted.
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
| `/protect_be <ticket>` | Move stop loss to break-even. |
| `/protect_trail <ticket> [ratio]` | Trail stop to lock in profit. |

## Version

Built with [discord.py](requirements.txt) and Python 3.11.

## Runtime Sharing

Both the bot and the REST API load the `PulseKernel` in their process. Sharing this
runtime means commands and API calls operate on the same risk metrics, journal
entries, and configuration, avoiding duplicated state or divergent trading logic.
