# Discord Moderation Bot

A Discord bot that automatically detects and responds to inappropriate language in chat messages.

## Features

- **Automatic Language Detection**: Uses better-profanity library with custom word filtering
- **Configurable Sensitivity**: Three levels (low, medium, high) for different server needs
- **Multiple Actions**: Warn, timeout, kick, or ban users for violations
- **Custom Word Lists**: Add server-specific words to filter or whitelist
- **Admin Commands**: Full configuration interface for server administrators
- **Logging**: Optional logging to designated channels
- **Bypass Protection**: Detects common bypass attempts (leetspeak, spacing, etc.)

## Setup Instructions

### 1. Create a Discord Bot

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications)
2. Click "New Application" and give it a name
3. Go to the "Bot" section
4. Click "Add Bot"
5. Copy the bot token (you'll need this later)
6. Under "Privileged Gateway Intents", enable:
   - Message Content Intent
   - Server Members Intent

### 2. Install Dependencies

Install the required Python packages:

```bash
pip install discord.py better-profanity python-dotenv
