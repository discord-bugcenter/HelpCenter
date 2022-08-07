from __future__ import annotations

import os
import typing

import discord
from discord.ext import commands

from utils import custom_errors
from utils.constants import BUG_CENTER_ID  # , LANGUAGE_ROLES
from utils.custom_command_tree import CustomCommandTree
from utils.logger import INFO, create_logger

if typing.TYPE_CHECKING:
    from logging import Logger

    from discord.ext.commands import Context


LOG_LEVEL = int(tmp) if (tmp := os.getenv("LOG_LEVEL")) and tmp.isdigit() else INFO
logger = create_logger(__name__, level=LOG_LEVEL)


class HelpCenterBot(commands.Bot):
    logger: Logger = logger

    def __init__(self) -> None:
        super().__init__(
            command_prefix=["/", "\\", "<@789210466492481597> ", "<@!789210466492481597> "],
            case_insensitive=True,
            tree_cls=CustomCommandTree,
            member_cache_flags=discord.MemberCacheFlags.all(),
            chunk_guilds_at_startup=True,
            allowed_mentions=discord.AllowedMentions.none(),
            intents=discord.Intents.all(),
        )

        self.initial_extensions: list[str] = [
            "cogs.lines",
            "cogs.googleit",
            "cogs.miscellaneous",
            "cogs.tag",
            "cogs.threads_help_tickets",
            "cogs.doc",
        ]

        # self.before_invoke(self.set_command_language)
        self.add_check(self.is_on_bug_center)

    async def setup_hook(self) -> None:
        for ext in self.initial_extensions:
            try:
                await self.load_extension(ext)
            except Exception as e:
                logger.error(f"Failed to load extension {ext}.", exc_info=e)

    async def on_ready(self) -> None:
        bot_user = typing.cast(discord.ClientUser, self.user)  # Bot is logged in, so it's a ClientUser

        await self.tree.sync(guild=discord.Object(id=BUG_CENTER_ID))

        activity = discord.Game("Have a nice day!")
        await self.change_presence(status=discord.Status.online, activity=activity)

        logger.info(f"Logged in as : {bot_user.name}")
        logger.info(f"ID : {bot_user.id}")

    def is_on_bug_center(self, ctx: commands.Context[HelpCenterBot]) -> bool:
        if ctx.guild and ctx.guild.id != BUG_CENTER_ID:
            raise custom_errors.NotInBugCenter()
        return True


if __name__ == "__main__":
    help_center_bot = HelpCenterBot()
    help_center_bot.run(os.environ["BOT_TOKEN"], reconnect=True)
