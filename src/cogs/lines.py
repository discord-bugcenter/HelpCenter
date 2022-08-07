from typing import TYPE_CHECKING

import discord
from discord import app_commands, ui
from discord.ext import commands
from typing_extensions import Self

from utils.constants import BUG_CENTER_ID

if TYPE_CHECKING:
    from main import HelpCenterBot


class LinesModal(ui.Modal, title="Add lines to your code"):
    language = ui.TextInput[Self](label="Language")
    code = ui.TextInput[Self](label="Code", style=discord.TextStyle.paragraph, min_length=5, max_length=1950)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        numbered_code: str = "\n".join(f"{i+1:>3} | {line}" for i, line in enumerate(str(self.code).splitlines()))

        await interaction.response.send_message(
            f"Numbered code of {interaction.user} :\n```{str(self.language) or ''}\n{numbered_code}\n```"
        )


class Lines(commands.Cog):
    def __init__(self, bot: HelpCenterBot) -> None:
        self.bot: HelpCenterBot = bot
        self.bot.tree.add_command(self.lines, guild=discord.Object(id=BUG_CENTER_ID))

    @app_commands.command(name="lines", description="Ajouter le numéro des lignes à votre code.")
    async def lines(self, inter: discord.Interaction) -> None:
        await inter.response.send_modal(LinesModal())


async def setup(bot: HelpCenterBot) -> None:
    await bot.add_cog(Lines(bot))
    bot.logger.info("Extension [lines] loaded successfully.")
