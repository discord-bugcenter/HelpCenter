from urllib import parse

from discord.ext import commands

from main import HelpCenterBot
from .utils import checkers
from .utils.misc import delete_with_emote
from .utils.i18n import use_current_gettext as _


class GoogleIt(commands.Cog):
    def __init__(self, bot: HelpCenterBot) -> None:
        """Allow you to transform a query to a google research using https://letmegooglethat.com."""
        self.bot = bot

    @commands.command(
        name='googleit',
        usage='/googleit {query}',
        aliases=['lmgt', 'letme'],
        description=_('Show how to do a google search :D')
    )
    @checkers.authorized_channels()
    async def google_it(self, ctx: commands.Context, *, string: str) -> None:  # Using string (with *, arg) instead of array (*arg) to prevent argument missing.
        """Return a url link that animate a google research."""
        stringed_array = " ".join(word[:50] for word in string.split(' ')[:32])  # Maximum of 32 words, and a word has 50 chars max.
        query = parse.quote_plus(stringed_array)

        response = await ctx.send(_("The google tool is very powerful, see how it works!\n") +
                                  f"<https://letmegooglethat.com/?q={query}>")
        await delete_with_emote(ctx, response)


def setup(bot: HelpCenterBot) -> None:
    bot.add_cog(GoogleIt(bot))
    bot.logger.info("Extension [google_it] loaded successfully.")
