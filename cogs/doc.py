from discord.ext import commands

from .utils import checkers
from .utils.misc import delete_with_emote
from .utils.i18n import use_current_gettext as _
import re


class Doc(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(
        name='doc',
        usage='/doc {query}',
        aliases=['docu', 'documentation'],
        description=_('Shows a documentation for discord.js or discord.py :D')
    )
    @checkers.authorized_channels()  # Using query (with *, arg) instead of array (*arg) to prevent argument missing.
    async def doc(self, ctx, doc_name, *, query):
        if re.findall(r'p|Py|Y', doc_name):
            response = await ctx.send(_("This is the api reference for {}!\n").format(query) +
                                      f"<https://discordpy.readthedocs.io/en/stable/api.html#{query}>")
        elif re.findall(r'j|Js|S', doc_name):
            response = await ctx.send(_("This is the api reference for {}!\n").format(query) +
                                      f"<https://discord.js.org/#/docs/main/stable/class/{query}>")
        else: return
        await delete_with_emote(ctx, response)


def setup(bot):
    bot.add_cog(Doc(bot))
    bot.logger.info("Extension [doc] loaded successfully.")
