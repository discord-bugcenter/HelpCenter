from typing import Optional, TYPE_CHECKING, Any

import discord
# from discord.ext import commands
from discord.app_commands import (
    ContextMenu,
    Command,
    AppCommandError,
    CommandTree,
    CommandInvokeError,
    CheckFailure,
    CommandNotFound
)

from utils import custom_errors as custom
# from .utils.codingame import NoPendingCOC
# from .utils.misc import Color
from utils.i18n import _

if TYPE_CHECKING:
    from main import HelpCenterBot  # , Context


class CustomCommandTree(CommandTree):
    def __init__(self, bot: 'HelpCenterBot') -> None:
        """Handle error for the bot commands."""
        self.bot = bot
        super().__init__(bot)

    @staticmethod
    async def send_error(inter: discord.Interaction, error_message: str):
        """A function to send an error message."""
        await inter.response.send_message(error_message)
        # embed = discord.Embed(
        #     title="<:error:797539791545565184> Erreur",
        #     url="https://discord.gg/Drbgufc",
        #     description=error_message,
        #     timestamp=ctx.message.created_at,
        #     color=Color.black().discord
        # )
        # embed.set_author(
        #     name=f'{ctx.author.name}#{ctx.author.discriminator}',
        #     icon_url=ctx.author.display_avatar.url
        # )
        # embed.set_footer(
        #     text=_(f"{ctx.bot.user.name}#{ctx.bot.user.discriminator} open-source project").format(**locals()),
        #     icon_url=ctx.bot.user.display_avatar.url
        # )

        # return await ctx.send(embed=embed, delete_after=10)

    async def on_error(self, inter: discord.Interaction, command: ContextMenu | Command[Any, (...), Any], error: AppCommandError) -> Optional[discord.Message]:
        """Function called when a command raise an error."""

        if isinstance(error, CommandNotFound):
            return

        # Custom errors :

        if isinstance(error, custom.NotAuthorizedChannels):
            formatted_text = (_("You can't execute this command in <#{inter.channel.id}>. Try in one of these channels :\n\n", inter).format(**locals()) +
                              f"<#{'>, <#'.join(str(channel_id) for channel_id in error.list_channels_id)}>")
            return await self.send_error(inter, formatted_text)
        if isinstance(error, custom.NotAuthorizedRoles):
            formatted_text = (_("You can't execute this command, you need one of these roles :\n\n", inter).format(**locals()) +
                              f"<@&{'>, <@&'.join(str(role_id) for role_id in error.list_roles_id)}>")
            return await self.send_error(inter, formatted_text)
        # if isinstance(error, custom.COCLinkNotValid):
        #     return await self.send_error(inter, _("You send an invalid link/code, or the game cannot be joined anymore, or the game doesn't exist !"))
        # if isinstance(error, custom.AlreadyProcessingCOC):
        #     return await self.send_error(inter, _("This clash is already published !"))

        # discord errors

        # if isinstance(error, PrivateMessageOnly):
        #     return await self.send_error(ctx, _('This command must be executed in Private Messages'))
        if isinstance(error, CheckFailure):
            return
        if isinstance(error, CommandInvokeError):
            if isinstance(error.__cause__, IndexError):
                return await self.send_error(inter, _("That query didn't provide enough results.", inter))
        if isinstance(error, AppCommandError):
            return await self.send_error(inter, str(error))

        # # Other errors

        # if isinstance(error, NoPendingCOC):
        #     return await self.send_error(ctx, _('There is no public coc started at the moment. Try again in a few seconds or go to https://www.codingame.com/multiplayer/clashofcode and click "Join a clash".'))

        self.bot.logger.error(error)  # if the error is not handled
