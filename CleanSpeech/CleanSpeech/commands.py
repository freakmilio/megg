import discord
from discord.ext import commands
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class AdminCommands(commands.Cog):
    def __init__(self, bot, config, moderation):
        self.bot = bot
        self.config = config
        self.moderation = moderation
    
    def is_admin():
        """Check if user has specific admin role permissions for freaky development server"""
        async def predicate(ctx):
            # Specific role IDs for freaky development server
            admin_role_ids = [1407906832248213505, 1407907000473489470]
            
            # Check if user has any of the admin roles
            user_role_ids = [role.id for role in ctx.author.roles]
            has_admin_role = any(role_id in admin_role_ids for role_id in user_role_ids)
            
            if not has_admin_role:
                # Delete the command message if user doesn't have permission
                try:
                    await ctx.message.delete()
                except discord.errors.NotFound:
                    pass  # Message already deleted
                except discord.errors.Forbidden:
                    pass  # No permission to delete
                return False
            
            return True
        return commands.check(predicate)
    
    @commands.command(name='modhelp')
    async def mod_help(self, ctx):
        """Show moderation bot help"""
        embed = discord.Embed(
            title="🛡️ Moderation Bot Help",
            description="Commands for managing the moderation bot",
            color=0x0099ff
        )
        
        embed.add_field(
            name="**Admin Commands**",
            value="`.modconfig` - Configure moderation settings\n"
                  "`.modstatus` - Show current configuration\n"
                  "`.modsensitivity <low|medium|high>` - Set sensitivity level\n"
                  "`.modaction <warn|timeout|kick|ban>` - Set action for violations\n"
                  "`.modtoggle` - Enable/disable moderation\n"
                  "`.modlogchannel [#channel]` - Set log channel",
            inline=False
        )
        
        embed.add_field(
            name="**Word Management**",
            value="`.modaddword <word>` - Add custom filtered word\n"
                  "`.modremoveword <word>` - Remove custom filtered word\n"
                  "`.modwhitelist <word>` - Add word to whitelist\n"
                  "`.modwords` - List custom words",
            inline=False
        )
        
        embed.add_field(
            name="**Sensitivity Levels**",
            value="**Low**: Only severe profanity\n"
                  "**Medium**: Moderate + severe profanity\n"
                  "**High**: Mild + moderate + severe profanity",
            inline=False
        )
        
        embed.set_footer(text="Note: Admin permissions required for configuration commands")
        await ctx.send(embed=embed)
    
    @commands.command(name='modconfig')
    @is_admin()
    async def mod_config(self, ctx):
        """Interactive configuration menu"""
        guild_config = self.config.get_guild_config(ctx.guild.id)
        
        embed = discord.Embed(
            title="🔧 Moderation Configuration",
            description="Current configuration for this server",
            color=0x00ff00 if guild_config['enabled'] else 0xff0000
        )
        
        # Status
        status = "✅ Enabled" if guild_config['enabled'] else "❌ Disabled"
        embed.add_field(name="Status", value=status, inline=True)
        
        # Sensitivity
        embed.add_field(name="Sensitivity", value=guild_config['sensitivity'].title(), inline=True)
        
        # Action
        embed.add_field(name="Action", value=guild_config['action'].title(), inline=True)
        
        # Skip admins
        skip_admins = "Yes" if guild_config['skip_admins'] else "No"
        embed.add_field(name="Skip Admins", value=skip_admins, inline=True)
        
        # Delete message
        delete_msg = "Yes" if guild_config['delete_message'] else "No"
        embed.add_field(name="Delete Messages", value=delete_msg, inline=True)
        
        # Log channel
        log_channel = "Not set"
        if guild_config['log_channel']:
            channel = self.bot.get_channel(guild_config['log_channel'])
            if channel:
                log_channel = channel.mention
        embed.add_field(name="Log Channel", value=log_channel, inline=True)
        
        # Custom words count
        custom_words_count = len(guild_config.get('custom_words', []))
        embed.add_field(name="Custom Words", value=str(custom_words_count), inline=True)
        
        # Whitelist count
        whitelist_count = len(guild_config.get('whitelist_words', []))
        embed.add_field(name="Whitelisted Words", value=str(whitelist_count), inline=True)
        
        embed.set_footer(text="Use individual commands to modify settings")
        await ctx.send(embed=embed)
    
    @commands.command(name='modstatus')
    async def mod_status(self, ctx):
        """Show moderation status"""
        guild_config = self.config.get_guild_config(ctx.guild.id)
        
        if guild_config['enabled']:
            embed = discord.Embed(
                title="✅ Moderation Active",
                description=f"Monitoring messages with **{guild_config['sensitivity']}** sensitivity",
                color=0x00ff00
            )
            embed.add_field(name="Action", value=guild_config['action'].title(), inline=True)
            embed.add_field(name="Skip Admins", value="Yes" if guild_config['skip_admins'] else "No", inline=True)
        else:
            embed = discord.Embed(
                title="❌ Moderation Disabled",
                description="Use `.modtoggle` to enable moderation",
                color=0xff0000
            )
        
        await ctx.send(embed=embed)
    
    @commands.command(name='modtoggle')
    @is_admin()
    async def mod_toggle(self, ctx):
        """Toggle moderation on/off"""
        guild_config = self.config.get_guild_config(ctx.guild.id)
        new_status = not guild_config['enabled']
        
        if self.config.update_guild_config(ctx.guild.id, {'enabled': new_status}):
            status = "enabled" if new_status else "disabled"
            embed = discord.Embed(
                title=f"✅ Moderation {status.title()}",
                description=f"Moderation has been {status} for this server",
                color=0x00ff00 if new_status else 0xff0000
            )
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(
                title="❌ Error",
                description="Failed to update configuration",
                color=0xff0000
            )
            await ctx.send(embed=embed)
    
    @commands.command(name='modsensitivity')
    @is_admin()
    async def mod_sensitivity(self, ctx, level: Optional[str] = None):
        """Set sensitivity level"""
        if level is None:
            embed = discord.Embed(
                title="Sensitivity Levels",
                description="Choose a sensitivity level:",
                color=0x0099ff
            )
            embed.add_field(name="Low", value="Only severe profanity", inline=False)
            embed.add_field(name="Medium", value="Moderate + severe profanity", inline=False)
            embed.add_field(name="High", value="Mild + moderate + severe profanity", inline=False)
            embed.set_footer(text="Usage: .modsensitivity <low|medium|high>")
            await ctx.send(embed=embed)
            return
        
        level = level.lower()
        if level not in ['low', 'medium', 'high']:
            embed = discord.Embed(
                title="❌ Invalid Level",
                description="Please choose: low, medium, or high",
                color=0xff0000
            )
            await ctx.send(embed=embed)
            return
        
        if self.config.update_guild_config(ctx.guild.id, {'sensitivity': level}):
            embed = discord.Embed(
                title="✅ Sensitivity Updated",
                description=f"Sensitivity level set to **{level}**",
                color=0x00ff00
            )
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(
                title="❌ Error",
                description="Failed to update sensitivity level",
                color=0xff0000
            )
            await ctx.send(embed=embed)
    
    @commands.command(name='modaction')
    @is_admin()
    async def mod_action(self, ctx, action: Optional[str] = None):
        """Set action for violations"""
        if action is None:
            embed = discord.Embed(
                title="Moderation Actions",
                description="Choose an action for violations:",
                color=0x0099ff
            )
            embed.add_field(name="warn", value="Send warning message", inline=False)
            embed.add_field(name="timeout", value="Warn + 10 minute timeout", inline=False)
            embed.add_field(name="kick", value="Warn + kick user", inline=False)
            embed.add_field(name="ban", value="Warn + ban user", inline=False)
            embed.set_footer(text="Usage: .modaction <warn|timeout|kick|ban>")
            await ctx.send(embed=embed)
            return
        
        action = action.lower()
        if action not in ['warn', 'timeout', 'kick', 'ban']:
            embed = discord.Embed(
                title="❌ Invalid Action",
                description="Please choose: warn, timeout, kick, or ban",
                color=0xff0000
            )
            await ctx.send(embed=embed)
            return
        
        if self.config.update_guild_config(ctx.guild.id, {'action': action}):
            embed = discord.Embed(
                title="✅ Action Updated",
                description=f"Violation action set to **{action}**",
                color=0x00ff00
            )
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(
                title="❌ Error",
                description="Failed to update action",
                color=0xff0000
            )
            await ctx.send(embed=embed)
    
    @commands.command(name='modlogchannel')
    @is_admin()
    async def mod_log_channel(self, ctx, channel: Optional[discord.TextChannel] = None):
        """Set log channel for moderation events"""
        if channel is None:
            # Show current log channel
            current_channel_id = self.config.get_log_channel(ctx.guild.id)
            if current_channel_id:
                current_channel = self.bot.get_channel(current_channel_id)
                if current_channel:
                    embed = discord.Embed(
                        title="Current Log Channel",
                        description=f"Log channel: {current_channel.mention}",
                        color=0x0099ff
                    )
                else:
                    embed = discord.Embed(
                        title="Log Channel Not Found",
                        description="The configured log channel no longer exists",
                        color=0xff0000
                    )
            else:
                embed = discord.Embed(
                    title="No Log Channel Set",
                    description="Use `.modlogchannel #channel` to set one",
                    color=0x0099ff
                )
            await ctx.send(embed=embed)
            return
        
        if self.config.set_log_channel(ctx.guild.id, channel.id):
            embed = discord.Embed(
                title="✅ Log Channel Set",
                description=f"Moderation logs will be sent to {channel.mention}",
                color=0x00ff00
            )
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(
                title="❌ Error",
                description="Failed to set log channel",
                color=0xff0000
            )
            await ctx.send(embed=embed)
    
    @commands.command(name='modaddword')
    @is_admin()
    async def mod_add_word(self, ctx, *, word: str):
        """Add custom word to filter"""
        if self.config.add_custom_word(ctx.guild.id, word):
            embed = discord.Embed(
                title="✅ Word Added",
                description=f"Added '{word}' to custom filter list",
                color=0x00ff00
            )
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(
                title="❌ Error",
                description="Failed to add word or word already exists",
                color=0xff0000
            )
            await ctx.send(embed=embed)
    
    @commands.command(name='modremoveword')
    @is_admin()
    async def mod_remove_word(self, ctx, *, word: str):
        """Remove custom word from filter"""
        if self.config.remove_custom_word(ctx.guild.id, word):
            embed = discord.Embed(
                title="✅ Word Removed",
                description=f"Removed '{word}' from custom filter list",
                color=0x00ff00
            )
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(
                title="❌ Error",
                description="Failed to remove word or word not found",
                color=0xff0000
            )
            await ctx.send(embed=embed)
    
    @commands.command(name='modwhitelist')
    @is_admin()
    async def mod_whitelist(self, ctx, *, word: str):
        """Add word to whitelist"""
        if self.config.add_whitelist_word(ctx.guild.id, word):
            embed = discord.Embed(
                title="✅ Word Whitelisted",
                description=f"Added '{word}' to whitelist",
                color=0x00ff00
            )
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(
                title="❌ Error",
                description="Failed to whitelist word",
                color=0xff0000
            )
            await ctx.send(embed=embed)
    
    @commands.command(name='modwords')
    @is_admin()
    async def mod_words(self, ctx):
        """List custom words and whitelist"""
        custom_words = self.config.get_custom_words(ctx.guild.id)
        whitelist_words = self.config.get_whitelist_words(ctx.guild.id)
        
        embed = discord.Embed(
            title="📝 Word Lists",
            description="Custom filtered and whitelisted words",
            color=0x0099ff
        )
        
        if custom_words:
            embed.add_field(
                name="Custom Filtered Words",
                value=", ".join(custom_words[:20]) + ("..." if len(custom_words) > 20 else ""),
                inline=False
            )
        else:
            embed.add_field(name="Custom Filtered Words", value="None", inline=False)
        
        if whitelist_words:
            embed.add_field(
                name="Whitelisted Words",
                value=", ".join(whitelist_words[:20]) + ("..." if len(whitelist_words) > 20 else ""),
                inline=False
            )
        else:
            embed.add_field(name="Whitelisted Words", value="None", inline=False)
        
        embed.set_footer(text=f"Total custom words: {len(custom_words)} | Total whitelisted: {len(whitelist_words)}")
        await ctx.send(embed=embed)

    @commands.command(name='modtest')
    @is_admin()
    async def mod_test(self, ctx, *, message: str):
        """Test if a message would be flagged"""
        is_profane, found_words = self.moderation.check_profanity(message, ctx.guild.id)
        
        if is_profane:
            embed = discord.Embed(
                title="🚨 Would be flagged",
                description=f"This message would be flagged for: {', '.join(found_words)}",
                color=0xff0000
            )
        else:
            embed = discord.Embed(
                title="✅ Would pass",
                description="This message would not be flagged",
                color=0x00ff00
            )
        
        await ctx.send(embed=embed, delete_after=15)
