import discord
from discord.ext import commands

from .utils import checkers
from .utils.i18n import use_current_gettext as _


class HelpCommand(commands.HelpCommand):
    def __init__(self):
        super().__init__(command_attrs={
            'description': _("Show bot commands.")
        })
        self.add_check(checkers.authorized_channels_check)

    async def on_help_command_error(self, ctx, error):
        print(error)

    async def send_error_message(self, error):
        embed = discord.Embed(
            title=_("An error occurred."),
            description=error
        )
        await self.context.send(embed=embed)

    async def send_bot_help(self, mapping):
        embed = discord.Embed(
            title=_("Here are my commands:"),
            description="\n".join([f"`{self.context.prefix}{cmd.name}` : {_(cmd.description)}" for cmd in self.context.bot.commands])
        )
        await self.context.send(embed=embed)

    async def send_command_help(self, command):
        embed = discord.Embed(
            title=f"{command.name}",
            description=command.description
        )
        embed.add_field(
            name="Usage:",
            value=command.usage
        )
        await self.context.send(embed=embed)

    async def command_not_found(self, string):
        return _("The command {string} way not found.").format(string)


def setup(bot):
    bot.help_command = HelpCommand()
    bot.logger.info("Extension [help] loaded successfully.")
