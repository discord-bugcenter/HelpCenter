import logging
import os

import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class HelpCenterBot(commands.Bot):

    def __init__(self):
        self.authorized_channels_id = [
            692712497844584448,  # discussion-dev
            595981741542604810,  # aide-dev
            707555362458304663,  # aide-dev-2
            779040873236136007,  # aide-dev-3
            754322079418941441,  # aide-autres
            780123502660681728,  # aide-autres-2
            595224241742413844,  # tests-1
            595224271132033024  # tests-2
        ]

        super().__init__(
            command_prefix="/",
            case_insensitive=True,
            fetch_offline_members=True,
            allowed_mentions=discord.AllowedMentions(everyone=False, roles=False, users=False),
            intents=discord.Intents.all()
        )
        
        self.logger = logger

        extensions = ['cogs.tag', 'cogs.help', 'cogs.command_error', 'cogs.miscellaneous']
        for extension in extensions:
            self.load_extension(extension)

    async def on_ready(self):
        activity = discord.Game("/tag <category> <tag>")
        await self.change_presence(status=discord.Status.idle, activity=activity)
        print(f"Logged in as : {self.user.name}\nID : {self.user.id}")

    def run(self):
        super().run(os.getenv("BOT_TOKEN"), reconnect=True)


help_center_bot = HelpCenterBot()
help_center_bot.run()
