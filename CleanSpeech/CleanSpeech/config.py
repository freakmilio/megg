import json
import os
import logging
from typing import Dict, Any, List, Optional
import discord

logger = logging.getLogger(__name__)

class Config:
    def __init__(self, config_file='config.json'):
        self.config_file = config_file
        self.default_config = {
            "global_settings": {
                "log_incidents": True,
                "default_action": "warn",
                "sensitivity_level": "medium",
                "skip_admins": True
            },
            "guilds": {}
        }
        self.config = self.load_config()
    
    def load_config(self) -> Dict[str, Any]:
        """Load configuration from file"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    # Merge with default config to ensure all keys exist
                    merged_config = self.default_config.copy()
                    merged_config.update(config)
                    return merged_config
            else:
                logger.info(f"Config file {self.config_file} not found, creating with defaults")
                self.save_config(self.default_config)
                return self.default_config.copy()
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            return self.default_config.copy()
    
    def save_config(self, config: Dict[str, Any] = None) -> bool:
        """Save configuration to file"""
        try:
            config_to_save = config if config is not None else self.config
            with open(self.config_file, 'w') as f:
                json.dump(config_to_save, f, indent=4)
            logger.info("Configuration saved successfully")
            return True
        except Exception as e:
            logger.error(f"Error saving config: {e}")
            return False
    
    def initialize_guild(self, guild_id: int) -> None:
        """Initialize default settings for a new guild"""
        guild_str = str(guild_id)
        if guild_str not in self.config['guilds']:
            self.config['guilds'][guild_str] = {
                "enabled": True,
                "action": self.config['global_settings']['default_action'],
                "sensitivity": self.config['global_settings']['sensitivity_level'],
                "skip_admins": self.config['global_settings']['skip_admins'],
                "custom_words": [],
                "whitelist_words": [],
                "log_channel": None,
                "warning_message": "Please keep your language appropriate for this server.",
                "delete_message": True,
                "warn_user": True
            }
            self.save_config()
    
    def get_guild_config(self, guild_id: int) -> Dict[str, Any]:
        """Get configuration for a specific guild"""
        guild_str = str(guild_id)
        if guild_str not in self.config['guilds']:
            self.initialize_guild(guild_id)
        return self.config['guilds'][guild_str]
    
    def update_guild_config(self, guild_id: int, updates: Dict[str, Any]) -> bool:
        """Update configuration for a specific guild"""
        try:
            guild_str = str(guild_id)
            if guild_str not in self.config['guilds']:
                self.initialize_guild(guild_id)
            
            self.config['guilds'][guild_str].update(updates)
            return self.save_config()
        except Exception as e:
            logger.error(f"Error updating guild config: {e}")
            return False
    
    def is_moderation_enabled(self, guild_id: int) -> bool:
        """Check if moderation is enabled for a guild"""
        guild_config = self.get_guild_config(guild_id)
        return guild_config.get('enabled', True)
    
    def get_sensitivity_level(self, guild_id: int) -> str:
        """Get sensitivity level for a guild"""
        guild_config = self.get_guild_config(guild_id)
        return guild_config.get('sensitivity', 'medium')
    
    def get_action(self, guild_id: int) -> str:
        """Get the action to take when inappropriate content is detected"""
        guild_config = self.get_guild_config(guild_id)
        return guild_config.get('action', 'warn')
    
    def should_skip_admin(self, guild_id: int, user: discord.Member) -> bool:
        """Check if we should skip moderation for admin users"""
        guild_config = self.get_guild_config(guild_id)
        skip_admins = guild_config.get('skip_admins', True)
        
        if not skip_admins:
            return False
        
        # Check if user has admin permissions
        return user.guild_permissions.administrator or user.guild_permissions.manage_messages
    
    def get_custom_words(self, guild_id: int) -> List[str]:
        """Get custom words to filter for a guild"""
        guild_config = self.get_guild_config(guild_id)
        return guild_config.get('custom_words', [])
    
    def add_custom_word(self, guild_id: int, word: str) -> bool:
        """Add a custom word to filter"""
        try:
            guild_str = str(guild_id)
            if guild_str not in self.config['guilds']:
                self.initialize_guild(guild_id)
            
            custom_words = self.config['guilds'][guild_str].get('custom_words', [])
            if word.lower() not in [w.lower() for w in custom_words]:
                custom_words.append(word.lower())
                self.config['guilds'][guild_str]['custom_words'] = custom_words
                return self.save_config()
            return True
        except Exception as e:
            logger.error(f"Error adding custom word: {e}")
            return False
    
    def remove_custom_word(self, guild_id: int, word: str) -> bool:
        """Remove a custom word from filter"""
        try:
            guild_str = str(guild_id)
            if guild_str not in self.config['guilds']:
                return False
            
            custom_words = self.config['guilds'][guild_str].get('custom_words', [])
            custom_words = [w for w in custom_words if w.lower() != word.lower()]
            self.config['guilds'][guild_str]['custom_words'] = custom_words
            return self.save_config()
        except Exception as e:
            logger.error(f"Error removing custom word: {e}")
            return False
    
    def get_whitelist_words(self, guild_id: int) -> List[str]:
        """Get whitelisted words for a guild"""
        guild_config = self.get_guild_config(guild_id)
        return guild_config.get('whitelist_words', [])
    
    def add_whitelist_word(self, guild_id: int, word: str) -> bool:
        """Add a word to whitelist"""
        try:
            guild_str = str(guild_id)
            if guild_str not in self.config['guilds']:
                self.initialize_guild(guild_id)
            
            whitelist_words = self.config['guilds'][guild_str].get('whitelist_words', [])
            if word.lower() not in [w.lower() for w in whitelist_words]:
                whitelist_words.append(word.lower())
                self.config['guilds'][guild_str]['whitelist_words'] = whitelist_words
                return self.save_config()
            return True
        except Exception as e:
            logger.error(f"Error adding whitelist word: {e}")
            return False
    
    def get_log_channel(self, guild_id: int) -> Optional[int]:
        """Get log channel ID for a guild"""
        guild_config = self.get_guild_config(guild_id)
        return guild_config.get('log_channel')
    
    def set_log_channel(self, guild_id: int, channel_id: int) -> bool:
        """Set log channel for a guild"""
        return self.update_guild_config(guild_id, {'log_channel': channel_id})
    
    def get_warning_message(self, guild_id: int) -> str:
        """Get warning message for a guild"""
        guild_config = self.get_guild_config(guild_id)
        return guild_config.get('warning_message', 'Please keep your language appropriate for this server.')
