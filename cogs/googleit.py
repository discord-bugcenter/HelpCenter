from typing import TYPE_CHECKING
from urllib import parse

from disnake.ext import commands
from disnake import ApplicationCommandInteraction

from .utils import checkers
from .utils.misc import delete_with_emote
from .utils.i18n import use_current_gettext as _
from .utils.constants import BUG_CENTER_ID

if TYPE_CHECKING:
    from main import HelpCenterBot


class GoogleIt(commands.Cog):
    def __init__(self, bot: 'HelpCenterBot') -> None:
        """Allow you to transform a query to a google research using https://letmegooglethat.com."""
        self.bot = bot

    @commands.slash_command(
        name='googleit',
        usage='/googleit {query}',
        description=_('Show how to do a google search :D'),
        guild_ids=[BUG_CENTER_ID]
    )
    @checkers.authorized_channels()
    async def google_it(self, inter: ApplicationCommandInteraction, search: str) -> None:  # Using string (with *, arg) instead of array (*arg) to prevent argument missing.
        """Return an url link that animate a google research."""

        stringed_array = " ".join(word[:50] for word in search.split(' ')[:32])  # Maximum of 32 words, and a word has 50 chars max.
        query = parse.quote_plus(stringed_array)

        await inter.response.send_message(_("The google tool is very powerful, see how it works!\n") +
                                          f"<https://googlethatforyou.com/?q={query}>")
        await delete_with_emote(self.bot, inter.author, await inter.original_message())


def setup(bot: 'HelpCenterBot') -> None:
    bot.add_cog(GoogleIt(bot))
    bot.logger.info("Extension [google_it] loaded successfully.")
