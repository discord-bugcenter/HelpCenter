import discord
from discord.ext import commands
from discord.ext.commands import errors

from .utils import custom_errors
from .utils.i18n import use_current_gettext as _


class CommandError(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @staticmethod
    async def send_error(ctx, error_message):
        embed = discord.Embed(
            title="<:error:797539791545565184> Erreur",
            url="https://discord.gg/Drbgufc",
            description=error_message,
            timestamp=ctx.message.created_at,
            color=discord.Color.from_rgb(0, 0, 0)
        )
        embed.set_author(
            name=f'{ctx.author.name}#{ctx.author.discriminator}',
            icon_url=ctx.author.avatar_url
        )
        embed.set_footer(
            text=_("{ctx.bot.user.name}#{ctx.bot.user.discriminator} open-source project").format(**locals()),
            icon_url=ctx.bot.user.avatar_url
        )

        await ctx.send(embed=embed, delete_after=10)

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if isinstance(error, errors.CommandNotFound):
            pass

        elif isinstance(error, custom_errors.NotAuthorizedChannels):
            formatted_text = (_("You can't execute this command in <#{error.channel.id}>. Try in one of these channels :\n\n").format(**locals()) +
                              f"<#{'>, <#'.join(str(chan_id) for chan_id in ctx.bot.authorized_channels_id)}>")
            return await self.send_error(ctx, formatted_text)
        elif isinstance(error, commands.MissingRequiredArgument):
            formatted_text = (_("A required argument is missing in the command !\n") +
                              f"`{ctx.command.usage}`")
            return await self.send_error(ctx, formatted_text)
        elif isinstance(error, errors.PrivateMessageOnly):
            return await self.send_error(ctx, _('This command must be executed in Private Messages'))
        elif isinstance(error, commands.CommandError):
            return await self.send_error(ctx, str(error))
        else:
            self.bot.logger.error(error)


def setup(bot):
    bot.add_cog(CommandError(bot))
    bot.logger.info("Extension [command_error] loaded successfully.")

