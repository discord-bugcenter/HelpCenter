import discord
from discord.ext import commands

from .utils import checkers

from urllib import parse

class LetMe(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(
        name='letme',
        usage='/letme {query}',
        description='Montrer comment faire une recherche google :D'
    )
    @checkers.authorized_channels()
    async def letme(self, ctx, *, array):
        query = parse.quote_plus(array)

        if not query:
            raise commands.CommandError('Vous devez mettre une rechercher dans votre message ! *Regardez `/help`*')

        await ctx.send(f'Comment rechercher **{array}** sur google\n**SUIS LE LIEN SUIVANT** --> https://letmegooglethat.com/?q={query}')
        await ctx.message.delete()

def setup(bot):
    bot.add_cog(LetMe(bot))