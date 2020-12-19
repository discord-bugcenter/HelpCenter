import logging
import os

import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class HelpCenterBot(commands.Bot):

    def __init__(self):
        intents = discord.Intents.all()

        super().__init__(
            command_prefix="!",
            case_insensitive=True,
            fetch_offline_members=True,
            allowed_mentions=discord.AllowedMentions(everyone=False, roles=False, users=False),
            intents=intents
        )
        
        self.logger = logger

        extensions = ['cogs.tag', 'cogs.tests']
        for extension in extensions:
            self.load_extension(extension)

    async def on_ready(self):
        print(f"Logged in as : {self.user.name}\nID : {self.user.id}")

    def run(self):
        super().run(os.getenv("BOT_TOKEN"), reconnect=True)


help_center_bot = HelpCenterBot()
help_center_bot.run()
