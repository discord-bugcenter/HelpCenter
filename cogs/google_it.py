from urllib import parse

from discord.ext import commands

from .utils import checkers


class GoogleIt(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(
        name='googleit',
        usage='/googleit {query}',
        aliases=['lmgt', 'letme'],
        description='Montrer comment faire une recherche google :D'
    )
    @checkers.authorized_channels()
    async def google_it(self, ctx, *, array):
        query = parse.quote_plus(array)

        if not query:
            raise commands.CommandError('Vous devez mettre une rechercher dans votre message ! *Regardez `/help`*')

        await ctx.send("L'outil google est fort puissant, regarde comment ça marche !\n"
                       f"https://letmegooglethat.com/?q={query}")
        await ctx.message.delete()


def setup(bot):
    bot.add_cog(GoogleIt(bot))
    bot.logger.info("Extension [google_it] loaded successfully.")
