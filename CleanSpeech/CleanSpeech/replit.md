# Discord Moderation Bot

## Overview

This is a Discord moderation bot designed to automatically detect and respond to inappropriate language in chat messages. The bot provides configurable content filtering with multiple sensitivity levels, various punishment actions, and comprehensive administration tools. It features bypass detection, custom word management, and logging capabilities to help server administrators maintain a safe chat environment.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Core Components

**Bot Architecture**: Built using discord.py framework with a command-based architecture. The main bot class (`ModerationBot`) extends `commands.Bot` and coordinates between different components through dependency injection.

**Configuration Management**: Centralized JSON-based configuration system (`Config` class) that handles both global settings and per-guild customization. Configuration is persisted to disk and provides default fallbacks for missing settings.

**Moderation Engine**: Separate `ModerationHandler` class that encapsulates all content filtering logic. Uses the better-profanity library as the base filtering engine, enhanced with custom word lists and bypass detection algorithms.

**Command System**: Modular command structure using discord.py's Cog system (`AdminCommands`). Admin commands are protected with permission checks and provide a complete configuration interface.

### Content Filtering Strategy

**Multi-level Sensitivity**: Three-tiered filtering system (low, medium, high) with progressively stricter word detection. Each level includes different word categories from mild to severe.

**Bypass Detection**: Pattern matching system to detect common evasion techniques including leetspeak substitution, character spacing, and symbol replacement.

**Custom Word Management**: Per-server custom word lists and whitelists that extend or override the base filtering rules.

### Action System

**Graduated Responses**: Configurable punishment actions including warn, timeout, kick, and ban. Actions can be customized per server based on community standards.

**Admin Protection**: Built-in skip functionality for administrators and moderators to prevent accidental actions on staff members.

**Incident Logging**: Optional logging system that can record violations to designated channels for moderation review.

### Data Storage

**File-based Configuration**: Simple JSON file storage for bot configuration, eliminating database dependencies while maintaining persistence.

**In-memory Processing**: Runtime data like incident tracking and normalized text processing happens in memory for performance.

## External Dependencies

**Discord API**: Core bot functionality through discord.py library for message handling, user management, and server interactions.

**Better Profanity Library**: Primary content filtering engine that provides baseline inappropriate content detection.

**Python Standard Library**: JSON for configuration management, logging for incident tracking, regex for pattern matching, and datetime for timestamping.

**File System**: Local file storage for configuration persistence and log file generation.