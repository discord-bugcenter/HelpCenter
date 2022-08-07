from __future__ import annotations

from typing import TYPE_CHECKING
from urllib import parse

import discord
from discord import app_commands
from discord.ext import commands

from utils.constants import BUG_CENTER_ID

if TYPE_CHECKING:
    from main import HelpCenterBot


class GoogleIt(commands.Cog):
    def __init__(self, bot: HelpCenterBot) -> None:
        """Allow you to transform a query to a google research using https://letmegooglethat.com."""
        self.bot: HelpCenterBot = bot
        self.bot.tree.add_command(self.google_it, guild=discord.Object(id=BUG_CENTER_ID))

    @app_commands.command(
        name="googleit",
        description="Show how to do a google search :D",
    )
    async def google_it(
        self, inter: discord.Interaction, search: str
    ) -> None:  # Using string (with *, arg) instead of array (*arg) to prevent argument missing.
        """Return an url link that animate a google research."""

        stringed_array = " ".join(
            word[:50] for word in search.split(" ")[:32]
        )  # Maximum of 32 words, and a word has 50 chars max.
        query = parse.quote_plus(stringed_array)

        await inter.response.send_message(
            f"The google tool is very powerful, see how it works!\n<https://googlethatforyou.com/?q={query}>"
        )


async def setup(bot: HelpCenterBot) -> None:
    await bot.add_cog(GoogleIt(bot))
    bot.logger.info("Extension [google_it] loaded successfully.")