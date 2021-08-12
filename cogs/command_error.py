from typing import Optional

import discord
from discord.ext import commands

from main import HelpCenterBot
from .utils import custom_errors
from .utils.codingame import NoPendingCOC
from .utils.misc import Color
from .utils.i18n import use_current_gettext as _


class CommandError(commands.Cog):
    def __init__(self, bot: HelpCenterBot) -> None:
        """Handle error for the bot commands."""
        self.bot = bot

    @staticmethod
    async def send_error(ctx: commands.Context, error_message: str) -> discord.Message:
        """A function to send an error message."""
        embed = discord.Embed(
            title="<:error:797539791545565184> Erreur",
            url="https://discord.gg/Drbgufc",
            description=error_message,
            timestamp=ctx.message.created_at,
            color=Color.black().discord
        )
        embed.set_author(
            name=f'{ctx.author.name}#{ctx.author.discriminator}',
            icon_url=ctx.author.avatar.url
        )
        embed.set_footer(
            text=_("{ctx.bot.user.name}#{ctx.bot.user.discriminator} open-source project").format(**locals()),
            icon_url=ctx.bot.user.avatar.url
        )

        return await ctx.send(embed=embed, delete_after=10)

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error: Exception) -> Optional[discord.Message]:
        """Function called when a command raise an error."""
        await self.bot.set_actual_language(ctx.author)

        if isinstance(error, commands.CommandNotFound):
            return

        # Custom errors :

        if isinstance(error, custom_errors.NotAuthorizedChannels):
            formatted_text = (_("You can't execute this command in <#{ctx.channel.id}>. Try in one of these channels :\n\n").format(**locals()) +
                              f"<#{'>, <#'.join(str(channel_id) for channel_id in error.list_channels_id)}>")
            return await self.send_error(ctx, formatted_text)
        if isinstance(error, custom_errors.NotAuthorizedRoles):
            formatted_text = (_("You can't execute this command, you need one of these roles :\n\n").format(**locals()) +
                              f"<@&{'>, <@&'.join(str(role_id) for role_id in error.list_roles_id)}>")
            return await self.send_error(ctx, formatted_text)
        if isinstance(error, custom_errors.COCLinkNotValid):
            return await self.send_error(ctx, _("You send an invalid link/code, or the game cannot be joined anymore, or the game doesn't exist !"))
        if isinstance(error, custom_errors.AlreadyProcessingCOC):
            return await self.send_error(ctx, _("This clash is already published !"))

        # Discord.py errors

        if isinstance(error, commands.MissingRequiredArgument):
            formatted_text = (_("A required argument is missing in the command !\n") +
                              f"`{ctx.command.usage}`")
            return await self.send_error(ctx, formatted_text)
        if isinstance(error, commands.PrivateMessageOnly):
            return await self.send_error(ctx, _('This command must be executed in Private Messages'))
        if isinstance(error, commands.CheckFailure):
            return
        if isinstance(error, commands.CommandError):
            return await self.send_error(ctx, str(error))

        # Other errors

        if isinstance(error, NoPendingCOC):
            return await self.send_error(ctx, _('There is not public coc started at the moment. Try again in a few seconds or go to https://www.codingame.com/multiplayer/clashofcode and click "Join a clash".'))

        self.bot.logger.error(error)  # if the error is not handled


def setup(bot: HelpCenterBot) -> None:
    bot.add_cog(CommandError(bot))
    bot.logger.info("Extension [command_error] loaded successfully.")
