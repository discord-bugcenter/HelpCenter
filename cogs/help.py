from typing import Optional, Coroutine, Any, cast
import discord
from discord.ext import commands

from main import HelpCenterBot
from .utils import checkers, misc
from .utils.i18n import use_current_gettext as _


class HelpCommand(commands.HelpCommand):
    def __init__(self) -> None:
        """Help command will allow the user to see the command list and ask for specific help for each commands."""
        super().__init__(command_attrs={
            'description': _("Show bot commands.")
        })
        self.add_check(checkers.authorized_channels_check)

    async def on_help_command_error(self, ctx: commands.Context, error: Exception) -> None:
        print(error)

    async def send_error_message(self, error: Exception) -> None:
        embed = discord.Embed(
            title=_("An error occurred."),
            description=error,
            color=misc.Color.black().discord
        )
        await self.context.send(embed=embed)

    async def send_bot_help(self, mapping) -> None:
        """Show the bot commands."""
        prefix = "\\" if str(self.context.bot.user.id) in cast(str, self.context.prefix) else self.context.prefix
        embed = discord.Embed(
            title=_("Here are my commands:"),
            description="\n".join([f"`{prefix}{cmd.name}` : {_(cmd.description)}" for cmd in self.context.bot.commands if not cmd.hidden]),
            color=misc.Color.grey_embed().discord
        )
        await self.context.send(embed=embed)

    async def send_command_help(self, command: commands.Command) -> Optional[Coroutine[Any, Any, str]]:
        """Show help for a specific command."""
        if command.hidden:
            return self.command_not_found(command.name)

        embed = discord.Embed(
            title=f"{command.name}",
            description=command.description,
            color=misc.Color.grey_embed().discord
        )
        embed.add_field(
            name="Usage:",
            value=command.usage
        )
        await self.context.send(embed=embed)

    async def command_not_found(self, string: str) -> str:
        """Message if the command is not found."""
        return _("The command {string} way not found.").format(string)


def setup(bot: HelpCenterBot) -> None:
    bot.help_command = HelpCommand()
    bot.logger.info("Extension [help] loaded successfully.")
