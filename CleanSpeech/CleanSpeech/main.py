import discord
from discord.ext import commands
import logging
import json
import os
from datetime import datetime
from dotenv import load_dotenv
from flask import Flask
import threading
import asyncio
import random

# Load environment variables
load_dotenv()
from config import Config
from moderation import ModerationHandler
from commands import AdminCommands

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('moderation_bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Create Flask app for UptimeRobot monitoring
app = Flask(__name__)

@app.route('/')
def home():
    return "Discord Moderation Bot is running!"

@app.route('/health')
def health():
    return {"status": "healthy", "bot": "online"}, 200

@app.route('/ping')
def ping():
    return "pong"

def run_web_server():
    """Run the Flask web server"""
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)

class ModerationBot(commands.Bot):
    def __init__(self):
        # Define intents
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        intents.members = True
        
        super().__init__(
            command_prefix='.',
            intents=intents,
            help_command=commands.DefaultHelpCommand()
        )
        
        # Initialize configuration and handlers
        self.config = Config()
        self.moderation = ModerationHandler(self.config)
        
        # Track incidents
        self.incident_count = 0
        
        # Status cycling
        self.status_list = [
            {"type": discord.ActivityType.watching, "name": "OK K.O.! (and you 😉)"},
            {"type": discord.ActivityType.playing, "name": "lots of roblox"},
            {"type": discord.ActivityType.listening, "name": "magdalena bay"},
            {"type": discord.ActivityType.listening, "name": "deee-lite"},
            {"type": discord.ActivityType.listening, "name": "djf"}
        ]
        self.status_task = None
        
    async def setup_hook(self):
        """Called when the bot is starting up"""
        try:
            # Add admin commands cog
            await self.add_cog(AdminCommands(self, self.config, self.moderation))
            logger.info("Admin commands loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load admin commands: {e}")
    
    async def on_ready(self):
        """Called when bot successfully connects to Discord"""
        logger.info(f'{self.user} has connected to Discord!')
        logger.info(f'Bot is in {len(self.guilds)} guilds')
        
        # Start the status cycling task
        self.status_task = asyncio.create_task(self.cycle_status())
        
        # Log guild information
        for guild in self.guilds:
            logger.info(f'Connected to guild: {guild.name} (ID: {guild.id})')
    
    async def cycle_status(self):
        """Cycle through different status messages every 15 seconds"""
        await self.wait_until_ready()
        
        while not self.is_closed():
            try:
                # Pick a random status from the list
                status_data = random.choice(self.status_list)
                
                activity = discord.Activity(
                    type=status_data["type"],
                    name=status_data["name"]
                )
                
                await self.change_presence(
                    status=discord.Status.online,
                    activity=activity
                )
                
                logger.info(f"Changed status to: {status_data['type'].name} {status_data['name']}")
                
                # Wait 15 seconds before changing again
                await asyncio.sleep(15)
                
            except Exception as e:
                logger.error(f"Error cycling status: {e}")
                await asyncio.sleep(15)  # Wait before trying again
    
    async def on_guild_join(self, guild):
        """Called when bot joins a new guild"""
        logger.info(f'Joined new guild: {guild.name} (ID: {guild.id})')
        
        # Initialize guild-specific settings if needed
        self.config.initialize_guild(guild.id)
        
        # Try to send a welcome message to the system channel
        if guild.system_channel and guild.system_channel.permissions_for(guild.me).send_messages:
            embed = discord.Embed(
                title="Moderation Bot Added!",
                description="Thanks for adding me to your server! Use `.modhelp` to see available commands.",
                color=0x00ff00
            )
            embed.add_field(
                name="Getting Started",
                value="• Use `.modconfig` to configure moderation settings\n"
                      "• Use `.modstatus` to check current configuration\n"
                      "• I'll automatically moderate messages based on your settings",
                inline=False
            )
            try:
                await guild.system_channel.send(embed=embed)
            except Exception as e:
                logger.warning(f"Could not send welcome message to {guild.name}: {e}")
    
    async def on_message(self, message):
        """Handle incoming messages for moderation"""
        # Ignore bot messages and DMs
        if message.author.bot or not message.guild:
            return
        
        # Check if an administrator pinged the bot
        if self.user in message.mentions and message.author.guild_permissions.administrator:
            await message.channel.send(f"heyyy {message.author.name}!")
            return
        
        # Process commands first
        await self.process_commands(message)
        
        # Skip moderation for admins if configured
        if self.config.should_skip_admin(message.guild.id, message.author):
            return
        
        # Check if moderation is enabled for this guild
        if not self.config.is_moderation_enabled(message.guild.id):
            return
        
        # Perform moderation check
        await self.moderation.check_message(message, self)
    
    async def on_command_error(self, ctx, error):
        """Handle command errors"""
        if isinstance(error, commands.CommandNotFound):
            return  # Ignore unknown commands
        
        elif isinstance(error, commands.MissingPermissions):
            embed = discord.Embed(
                title="Permission Error",
                description="You don't have the required permissions to use this command.",
                color=0xff0000
            )
            await ctx.send(embed=embed, delete_after=10)
        
        elif isinstance(error, commands.BotMissingPermissions):
            embed = discord.Embed(
                title="Bot Permission Error",
                description=f"I'm missing the following permissions: {', '.join(error.missing_permissions)}",
                color=0xff0000
            )
            await ctx.send(embed=embed, delete_after=15)
        
        elif isinstance(error, commands.CommandOnCooldown):
            embed = discord.Embed(
                title="Command on Cooldown",
                description=f"Please wait {error.retry_after:.1f} seconds before using this command again.",
                color=0xffaa00
            )
            await ctx.send(embed=embed, delete_after=10)
        
        else:
            logger.error(f"Unhandled command error: {error}")
            embed = discord.Embed(
                title="Error",
                description="An unexpected error occurred. Please try again later.",
                color=0xff0000
            )
            await ctx.send(embed=embed, delete_after=10)

def main():
    """Main function to start the bot"""
    # Get Discord token from environment
    token = os.getenv('DISCORD_TOKEN')
    
    if not token:
        logger.error("DISCORD_TOKEN environment variable not found!")
        logger.error("Please set your Discord bot token in the environment variables.")
        return
    
    # Start web server in a separate thread for UptimeRobot monitoring
    web_thread = threading.Thread(target=run_web_server, daemon=True)
    web_thread.start()
    logger.info("Web server started on port 5000 for UptimeRobot monitoring")
    
    # Create and run the bot
    bot = ModerationBot()
    
    try:
        bot.run(token)
    except discord.LoginFailure:
        logger.error("Invalid Discord token provided!")
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")

if __name__ == '__main__':
    main()
