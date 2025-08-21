import discord
import logging
from better_profanity import profanity
from typing import List, Tuple, Optional
import re
import asyncio
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class ModerationHandler:
    def __init__(self, config):
        self.config = config
        
        # Initialize profanity filter
        profanity.load_censor_words()
        
        # Additional word lists for different sensitivity levels
        self.mild_words = [
            'damn', 'hell', 'crap', 'piss'
        ]
        
        self.moderate_words = [
            'ass', 'bitch', 'shit'
        ]
        
        # Severe words are handled by better-profanity by default
        
        # Common leetspeak and bypass patterns
        self.bypass_patterns = {
            '@': 'a',
            '3': 'e',
            '1': 'i',
            '0': 'o',
            '5': 's',
            '7': 't',
            '4': 'a',
            '$': 's',
            '+': 't'
        }
    
    def normalize_text(self, text: str) -> str:
        """Normalize text to catch common bypasses"""
        # Convert to lowercase
        normalized = text.lower()
        
        # Replace common substitutions
        for char, replacement in self.bypass_patterns.items():
            normalized = normalized.replace(char, replacement)
        
        # Remove spaces within potential bad words
        # This catches things like "b a d w o r d"
        normalized = re.sub(r'\s+', '', normalized)
        
        # Remove repeated characters (like "shiiiit" -> "shit")
        normalized = re.sub(r'(.)\1{2,}', r'\1', normalized)
        
        return normalized
    
    def has_moderation_bypass(self, user: discord.Member) -> bool:
        """Check if user has moderation bypass (specific roles + administrators)"""
        # Bypass role IDs: admin roles + additional bypass role
        bypass_role_ids = [1407906832248213505, 1407907000473489470, 1407906846303326279]
        
        # Check if user is administrator
        if user.guild_permissions.administrator:
            return True
        
        # Check if user has any bypass roles
        user_role_ids = [role.id for role in user.roles]
        has_bypass_role = any(role_id in bypass_role_ids for role_id in user_role_ids)
        
        return has_bypass_role
    
    def check_spam(self, message: str) -> Tuple[bool, str]:
        """Check if message contains spam (7+ repeated characters/emojis)"""
        # Check for 7+ consecutive repeated characters (including emojis)
        pattern = r'(.)\1{6,}'  # Same character repeated 7 or more times
        
        matches = re.findall(pattern, message)
        if matches:
            # Return True and the first repeated character found
            return True, f"Repeated character spam: '{matches[0]}'"
        
        return False, ""
    
    def check_profanity(self, message: str, guild_id: int) -> Tuple[bool, List[str]]:
        """Check if message contains profanity"""
        found_words = []
        
        # Get guild configuration
        sensitivity = self.config.get_sensitivity_level(guild_id)
        custom_words = self.config.get_custom_words(guild_id)
        whitelist_words = self.config.get_whitelist_words(guild_id)
        
        # Normalize the message
        normalized_message = self.normalize_text(message)
        original_lower = message.lower()
        
        # Check custom words first
        for word in custom_words:
            if word in original_lower or word in normalized_message:
                # Check if it's whitelisted
                if word not in whitelist_words:
                    found_words.append(word)
        
        # Check built-in profanity filter
        if profanity.contains_profanity(message) or profanity.contains_profanity(normalized_message):
            # Get the actual profane words
            profane_words = []
            words_in_message = message.split() + normalized_message.split()
            
            for word in words_in_message:
                if profanity.contains_profanity(word):
                    if word.lower() not in whitelist_words:
                        profane_words.append(word)
            
            found_words.extend(profane_words)
        
        # Check sensitivity level words
        words_to_check = []
        
        if sensitivity == 'low':
            words_to_check = []  # Only severe words (handled by better-profanity)
        elif sensitivity == 'medium':
            words_to_check = self.moderate_words
        elif sensitivity == 'high':
            words_to_check = self.mild_words + self.moderate_words
        
        for word in words_to_check:
            if word in original_lower or word in normalized_message:
                if word not in whitelist_words:
                    found_words.append(word)
        
        # Remove duplicates
        found_words = list(set(found_words))
        
        return len(found_words) > 0, found_words
    
    async def check_message(self, message: discord.Message, bot):
        """Check a message and take appropriate action"""
        try:
            if message.guild is None:
                return
            
            # Check if user has moderation bypass (specific roles + administrators)
            if self.has_moderation_bypass(message.author):
                return  # Skip all moderation for bypass users
            
            # Check for spam first
            is_spam, spam_reason = self.check_spam(message.content)
            if is_spam:
                await self.handle_spam(message, spam_reason, bot)
                return  # Don't check profanity if it's spam
            
            # Check for profanity
            is_profane, found_words = self.check_profanity(message.content, message.guild.id)
            
            if is_profane:
                await self.handle_inappropriate_content(message, found_words, bot)
                
        except Exception as e:
            logger.error(f"Error checking message: {e}")
    
    async def handle_inappropriate_content(self, message: discord.Message, found_words: List[str], bot):
        """Handle inappropriate content based on guild configuration"""
        try:
            if message.guild is None:
                return
            guild_config = self.config.get_guild_config(message.guild.id)
            action = guild_config.get('action', 'warn')
            
            # Log the incident
            await self.log_incident(message, found_words, bot)
            
            # Delete message if configured
            if guild_config.get('delete_message', True):
                try:
                    await message.delete()
                    guild_name = message.guild.name if message.guild else "Unknown"
                    logger.info(f"Deleted inappropriate message from {message.author} in {guild_name}")
                except discord.errors.NotFound:
                    pass  # Message already deleted
                except discord.errors.Forbidden:
                    guild_name = message.guild.name if message.guild else "Unknown"
                    logger.warning(f"No permission to delete messages in {guild_name}")
            
            # Take action based on configuration
            if action == 'warn':
                await self.warn_user(message, found_words)
            elif action == 'timeout':
                await self.timeout_user(message, found_words)
            elif action == 'kick':
                await self.kick_user(message, found_words)
            elif action == 'ban':
                await self.ban_user(message, found_words)
            
        except Exception as e:
            logger.error(f"Error handling inappropriate content: {e}")
    
    async def handle_spam(self, message: discord.Message, spam_reason: str, bot):
        """Handle spam messages with custom warning"""
        try:
            if message.guild is None:
                return
            
            # Delete the spam message
            try:
                await message.delete()
                guild_name = message.guild.name if message.guild else "Unknown"
                logger.info(f"Deleted spam message from {message.author} in {guild_name}: {spam_reason}")
            except discord.errors.NotFound:
                pass  # Message already deleted
            except discord.errors.Forbidden:
                guild_name = message.guild.name if message.guild else "Unknown"
                logger.warning(f"No permission to delete messages in {guild_name}")
            
            # Send simple DM warning
            try:
                await message.author.send("ok bro stop spamming")
                logger.info(f"Sent DM spam warning to {message.author}")
            except discord.errors.Forbidden:
                logger.info(f"Could not DM {message.author} - DMs are disabled")
            
            # Log the spam incident
            await self.log_spam_incident(message, spam_reason, bot)
            
        except Exception as e:
            logger.error(f"Error handling spam: {e}")
    
    async def log_spam_incident(self, message: discord.Message, spam_reason: str, bot):
        """Log spam incident"""
        try:
            # Console logging
            guild_name = message.guild.name if message.guild else "Unknown"
            logger.info(f"Spam detected: {message.author} in {guild_name} - {spam_reason}")
            
            # Channel logging if configured
            if message.guild is None:
                return
            log_channel_id = self.config.get_log_channel(message.guild.id)
            if log_channel_id:
                log_channel = bot.get_channel(log_channel_id)
                if log_channel:
                    embed = discord.Embed(
                        title="🚨 Spam Detection Log",
                        color=0xff6600,
                        timestamp=datetime.utcnow()
                    )
                    embed.add_field(name="User", value=f"{message.author} ({message.author.id})", inline=True)
                    channel_mention = getattr(message.channel, 'mention', f"#{message.channel.name}") if hasattr(message.channel, 'name') else "Unknown Channel"
                    embed.add_field(name="Channel", value=channel_mention, inline=True)
                    embed.add_field(name="Action", value="Spam Message Deleted", inline=True)
                    embed.add_field(name="Reason", value=spam_reason, inline=False)
                    embed.add_field(name="Original Message", value=message.content[:500] if message.content else "No content", inline=False)
                    
                    await log_channel.send(embed=embed)
        
        except Exception as e:
            logger.error(f"Error logging spam incident: {e}")
    
    async def warn_user(self, message: discord.Message, found_words: List[str]):
        """Send a warning to the user"""
        try:
            if message.guild is None:
                return
            guild_config = self.config.get_guild_config(message.guild.id)
            warning_message = guild_config.get('warning_message', 'Please keep your language appropriate for this server.')
            
            embed = discord.Embed(
                title="⚠️ Language Warning",
                description=warning_message,
                color=0xffaa00,
                timestamp=datetime.utcnow()
            )
            guild_name = message.guild.name if message.guild else "Unknown"
            embed.set_footer(text=f"Server: {guild_name}")
            
            # Try to send DM first, then channel message
            try:
                await message.author.send(embed=embed)
                logger.info(f"Sent DM warning to {message.author}")
            except discord.errors.Forbidden:
                # Can't send DM, send in channel
                embed.title = f"⚠️ {message.author.mention} - Language Warning"
                warning_msg = await message.channel.send(embed=embed, delete_after=15)
                logger.info(f"Sent channel warning to {message.author}")
        
        except Exception as e:
            logger.error(f"Error sending warning: {e}")
    
    async def timeout_user(self, message: discord.Message, found_words: List[str]):
        """Timeout the user for inappropriate language"""
        try:
            # First warn the user
            await self.warn_user(message, found_words)
            
            # Timeout for 10 minutes
            timeout_duration = 600  # 10 minutes in seconds
            
            if message.guild and message.guild.me.guild_permissions.moderate_members and hasattr(message.author, 'timeout'):
                await message.author.timeout(
                    discord.utils.utcnow() + timedelta(seconds=timeout_duration),
                    reason=f"Inappropriate language: {', '.join(found_words[:3])}"
                )
                
                embed = discord.Embed(
                    title="🔇 User Timed Out",
                    description=f"{message.author.mention} has been timed out for 10 minutes due to inappropriate language.",
                    color=0xff6600,
                    timestamp=datetime.utcnow()
                )
                await message.channel.send(embed=embed, delete_after=30)
                logger.info(f"Timed out {message.author} for inappropriate language")
            else:
                guild_name = message.guild.name if message.guild else "Unknown"
                logger.warning(f"No permission to timeout members in {guild_name}")
        
        except Exception as e:
            logger.error(f"Error timing out user: {e}")
    
    async def kick_user(self, message: discord.Message, found_words: List[str]):
        """Kick the user for inappropriate language"""
        try:
            # First warn the user
            await self.warn_user(message, found_words)
            
            if message.guild and message.guild.me.guild_permissions.kick_members and hasattr(message.author, 'kick'):
                await message.author.kick(reason=f"Inappropriate language: {', '.join(found_words[:3])}")
                
                embed = discord.Embed(
                    title="👢 User Kicked",
                    description=f"{message.author.mention} has been kicked for inappropriate language.",
                    color=0xff3300,
                    timestamp=datetime.utcnow()
                )
                await message.channel.send(embed=embed, delete_after=60)
                logger.info(f"Kicked {message.author} for inappropriate language")
            else:
                guild_name = message.guild.name if message.guild else "Unknown"
                logger.warning(f"No permission to kick members in {guild_name}")
        
        except Exception as e:
            logger.error(f"Error kicking user: {e}")
    
    async def ban_user(self, message: discord.Message, found_words: List[str]):
        """Ban the user for inappropriate language"""
        try:
            # First warn the user
            await self.warn_user(message, found_words)
            
            if message.guild and message.guild.me.guild_permissions.ban_members and hasattr(message.author, 'ban'):
                await message.author.ban(reason=f"Inappropriate language: {', '.join(found_words[:3])}")
                
                embed = discord.Embed(
                    title="🔨 User Banned",
                    description=f"{message.author.mention} has been banned for inappropriate language.",
                    color=0xff0000,
                    timestamp=datetime.utcnow()
                )
                await message.channel.send(embed=embed, delete_after=60)
                logger.info(f"Banned {message.author} for inappropriate language")
            else:
                guild_name = message.guild.name if message.guild else "Unknown"
                logger.warning(f"No permission to ban members in {guild_name}")
        
        except Exception as e:
            logger.error(f"Error banning user: {e}")
    
    async def log_incident(self, message: discord.Message, found_words: List[str], bot):
        """Log moderation incident"""
        try:
            # Console logging
            guild_name = message.guild.name if message.guild else "Unknown"
            logger.info(f"Inappropriate language detected: {message.author} in {guild_name} - Words: {found_words}")
            
            # Channel logging if configured
            if message.guild is None:
                return
            log_channel_id = self.config.get_log_channel(message.guild.id)
            if log_channel_id:
                log_channel = bot.get_channel(log_channel_id)
                if log_channel:
                    embed = discord.Embed(
                        title="🚨 Moderation Log",
                        color=0xff0000,
                        timestamp=datetime.utcnow()
                    )
                    embed.add_field(name="User", value=f"{message.author} ({message.author.id})", inline=True)
                    channel_mention = getattr(message.channel, 'mention', f"#{message.channel.name}") if hasattr(message.channel, 'name') else "Unknown Channel"
                    embed.add_field(name="Channel", value=channel_mention, inline=True)
                    embed.add_field(name="Action", value="Message Deleted", inline=True)
                    embed.add_field(name="Detected Words", value=", ".join(found_words[:5]), inline=False)
                    embed.add_field(name="Original Message", value=message.content[:500] if message.content else "No content", inline=False)
                    
                    await log_channel.send(embed=embed)
        
        except Exception as e:
            logger.error(f"Error logging incident: {e}")
