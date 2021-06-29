import logging
import os
from collections import OrderedDict
from typing import Union

import discord
from discord.ext import commands

from dotenv import load_dotenv
from cogs.utils import i18n, custom_errors


logging.basicConfig()
logger = logging.getLogger(__name__)

load_dotenv()

class HelpCenterBot(commands.Bot):

    def __init__(self):
        self.bug_center_id = 595218682670481418

        self.staff_roles = {
            'administrator': 713434163587579986,
            'assistant': 627445515159732224,
            'depister': 713452724603191367,
            'brillant': 713452621196820510,
            'normal': 627836152350769163
        }

        self.help_channels_id = [
            692712497844584448,  # discussion-dev
            595981741542604810,  # aide-dev
            707555362458304663,  # aide-dev-2
            779040873236136007,  # aide-dev-3
            810970318641954856,  # aide-dev-4
            754322079418941441,  # aide-autres
            780123502660681728,  # aide-autres-2
        ]
        self.test_channels_id = [
            595224241742413844,  # tests-1
            595224271132033024,  # tests-2
            595232117806333965,  # cmds-staff
            711599221220048989  # cmds-admin
        ]
        self.authorized_channels_id = self.test_channels_id + self.help_channels_id

        self.language_roles = OrderedDict((
            (797581355785125889, 'fr_FR'),
            (797581356749946930, 'en_EN')
        ))  # OrderedDict to make French in prior of English

        super().__init__(
            command_prefix="/",
            case_insensitive=True,
            member_cache_flags=discord.MemberCacheFlags.all(),
            chunk_guilds_at_startup=True,
            allowed_mentions=discord.AllowedMentions.none(),
            intents=discord.Intents.all()
        )
        
        self.logger = logger

        extensions = ['event', 'tag', 'help', 'command_error', 'miscellaneous', 'lines', 'google_it', 'doc']
        for extension in extensions:
            self.load_extension('cogs.'+extension)

        self.before_invoke(self.set_command_language)
        self.add_check(self.is_on_bug_center)

    async def on_ready(self):
        activity = discord.Game("/tag <category> <tag>")
        await self.change_presence(status=discord.Status.idle, activity=activity)
        print(f"Logged in as : {self.user.name}")
        print(f"ID : {self.user.id}")

    def is_on_bug_center(self, ctx):
        if ctx.guild and ctx.guild.id != self.bug_center_id:
            raise custom_errors.NotInBugCenter()
        return True

    async def set_command_language(self, ctx: commands.Context) -> None:  # function called when a command is executed
        await self.set_actual_language(ctx.author)

    async def set_actual_language(self, user: Union[discord.Member, discord.User]) -> None:
        i18n.current_locale.set(self.get_user_language(user))

    def get_user_language(self, user: Union[discord.Member, discord.User]) -> str:
        if not hasattr(user, 'guild') or user.guild.id != self.bug_center_id:  # if the function was executed in DM
            user = self.get_guild(self.bug_center_id).get_member(user.id)

        if user:
            for role_id, lang in self.language_roles.items():
                if discord.utils.get(user.roles, id=role_id):
                    return lang

        return 'en_EN'

    def run(self):
        super().run(os.getenv("BOT_TOKEN"), reconnect=True)

help_center_bot = HelpCenterBot()
help_center_bot.run()
