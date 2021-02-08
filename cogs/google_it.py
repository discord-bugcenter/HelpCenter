from urllib import parse

from discord.ext import commands

from .utils import checkers
from .utils.misc import delete_with_emote


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
    async def google_it(self, ctx, *, string):  # Using string (with *, arg) instead of array (*arg) to prevent argument missing.
        stringed_array = " ".join(word[:50] for word in string.split(' ')[:32])  # Maximum of 32 words, and a word has 50 chars max.
        query = parse.quote_plus(stringed_array)

        response = await ctx.send("L'outil google est fort puissant, regarde comment ça marche !\n"
                                  f"<https://letmegooglethat.com/?q={query}>")
        await delete_with_emote(ctx, response)


def setup(bot):
    bot.add_cog(GoogleIt(bot))
    bot.logger.info("Extension [google_it] loaded successfully.")
