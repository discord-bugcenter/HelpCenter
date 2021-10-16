import logging
import os
import typing

import discord
from discord.ext import commands
from dotenv import load_dotenv

from cogs.utils import i18n, custom_errors
from cogs.utils.constants import BUG_CENTER_ID, LANGUAGE_ROLES

if typing.TYPE_CHECKING:
    from cogs.utils import Person
    from discord.ext.commands import Context


load_dotenv()

logging.basicConfig()
logger = logging.getLogger(__name__)


class HelpCenterBot(commands.Bot):
    def __init__(self) -> None:
        super().__init__(
            command_prefix=["/", "\\", "<@789210466492481597> ", "<@!789210466492481597> "],
            case_insensitive=True,
            member_cache_flags=discord.MemberCacheFlags.all(),
            chunk_guilds_at_startup=True,
            allowed_mentions=discord.AllowedMentions.none(),
            intents=discord.Intents.all(),
            sync_commands=True
        )

        self.logger: logging.Logger = logger

        extensions: list[str] = ['clash_of_code', 'event', 'tag', 'help', 'command_error', 'miscellaneous', 'lines', 'google_it', 'doc', 'auto_help_system']
        for extension in extensions:
            self.load_extension('cogs.' + extension)

        self.before_invoke(self.set_command_language)
        self.add_check(self.is_on_bug_center)

    async def on_ready(self) -> None:
        activity = discord.Game("/tag <category> <tag>")
        await self.change_presence(status=discord.Status.idle, activity=activity)
        print(f"Logged in as : {self.user.name}")
        print(f"ID : {self.user.id}")

    def is_on_bug_center(self, ctx: 'Context[HelpCenterBot]') -> bool:
        if ctx.guild and ctx.guild.id != BUG_CENTER_ID:
            raise custom_errors.NotInBugCenter()
        return True

    async def set_command_language(self, ctx: 'Context[HelpCenterBot]') -> None:  # function called when a command is executed
        await self.set_actual_language(ctx.author)

    async def set_actual_language(self, person: 'Person') -> None:
        i18n.current_locale.set(self.get_user_language(person))

    def get_user_language(self, person: 'Person') -> str:
        if isinstance(person, discord.User) or person.guild.id != BUG_CENTER_ID:  # if the function was executed in DM
            if guild := self.get_guild(BUG_CENTER_ID):
                member = guild.get_member(person.id)
            else:
                member = None
        else:
            member = person

        if member:
            for role_id, lang in LANGUAGE_ROLES.items():
                if discord.utils.get(member.roles, id=role_id):
                    return lang

        return 'en_EN'

    def run(self) -> None:
        super().run(os.getenv("BOT_TOKEN"), reconnect=True)


if __name__ == "__main__":
    help_center_bot = HelpCenterBot()
    help_center_bot.run()
