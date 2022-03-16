from typing import TYPE_CHECKING

import discord
from discord.ext import commands
from discord import ui
from discord import app_commands

from cogs.utils.constants import BUG_CENTER_ID

# from .utils.misc import delete_with_emote
from .utils.i18n import _

if TYPE_CHECKING:
    from main import HelpCenterBot


LANGUAGES = ["python", "javascript", "typescript", "java", "rust", "lisp", "elixir"]


# async def lines_autocomplete(inter: discord.ApplicationCommandInteraction, user_input: str) -> list[str]:
#     return [lang for lang in LANGUAGES + [user_input] if user_input.lower() in lang]

class LinesModal(ui.Modal, title='Add lines to your code'):
    language = ui.TextInput(label='Language')
    code = ui.TextInput(label='Code', style=discord.TextStyle.paragraph, min_length=5, max_length=1950)

    async def on_submit(self, inter: discord.Interaction):

        numbered_code = '\n'.join(f'{i+1:>3} | {line}' for i, line in enumerate(str(self.code).splitlines()))

        await inter.response.send_message(_('Numbered code of {0} :\n').format(inter.user) +
                                          '```' + (str(self.language) or '') + '\n' +
                                          numbered_code +
                                          '\n```')
        # await delete_with_emote(inter.client, ctx.author, await ctx.original_message())


class Lines(commands.Cog):
    def __init__(self, bot: 'HelpCenterBot') -> None:
        self.bot = bot
        self.bot.tree.add_command(self.lines, guild=discord.Object(id=BUG_CENTER_ID))

    @app_commands.command(
        name='lines',
        description='Ajouter le numéro des lignes à votre code.'
    )
    async def lines(self, inter: discord.Interaction) -> None:
        await inter.response.send_modal(LinesModal())


async def setup(bot: 'HelpCenterBot') -> None:
    await bot.add_cog(Lines(bot))
    bot.logger.info("Extension [lines] loaded successfully.")
