import discord
from discord.ext import commands
from discord.ext.commands import errors

from .utils import custom_errors


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
            text=f"{ctx.bot.user.name}#{ctx.bot.user.discriminator} projet open-source",
            icon_url=ctx.bot.user.avatar_url
        )

        await ctx.send(embed=embed, delete_after=10)

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if isinstance(error, errors.CommandNotFound):
            pass

        elif isinstance(error, custom_errors.NotAuthorizedChannels):
            formated_text = (f"Vous ne pouvez pas exécuter cette commande dans <#{error.channel.id}>. Essayez dans l'un de ces salons :\n\n"
                             f"<#{'>, <#'.join(str(chan_id) for chan_id in ctx.bot.authorized_channels_id)}>")
            return await self.send_error(ctx, formated_text)
        elif isinstance(error, commands.CommandError):
            return await self.send_error(ctx, str(error))
        else:
            self.bot.logger.error(error)


def setup(bot):
    bot.add_cog(CommandError(bot))
    bot.logger.info("Extension [command_error] loaded successfully.")

