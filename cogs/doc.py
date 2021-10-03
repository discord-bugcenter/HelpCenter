import discord
from discord.ext import commands

from aiohttp import ClientSession

from .utils import checkers
from.utils.misc import delete_with_emote
from .utils.i18n import use_current_gettext as _

# TODO : this command should be recreated with a real research into documentations.

class Doc(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(
        name='doc',
        usage='/doc {query}',
        aliases=['documentation'],
        description=_('Shows 4 or fewer links referring to a documentation on readthedocs.io :D'),
        hidden=True
    )
    # Using query (with *, arg) instead of array (*arg) to prevent argument missing.
    @checkers.authorized_channels()
    async def doc(self, ctx, doc, *, query):
        
        url = 'https://readthedocs.org/api/v2/search/'
        params = {
            'q': query,
            'project': doc,
            'version': 'latest',
        }
        async with ClientSession() as session:
            async with session.get(url, params=params) as r:
                json = await r.json()
        embed = discord.Embed(title=_("{} Results (click here for a complete search)".format(json['count'])), description="", url="{}/en/stable/search.html?q={}".format(json['results'][0]['domain'], query))
        for result in json['results']:
            try:
                for block in result['blocks']:
                    embed.description += f"\n[{block['title']}]({result['domain']}{result['path']}?highlight={query}#{block['id']})"
            except KeyError:
                embed.description += f"\n[{result['title']}]({result['domain']}{result['path']}?highlight={query}#{block['id']})"
        desc = ""
        for line in embed.description.split('\n')[0:4]:
            desc += line + "\n"
        embed.description = desc
        embed.set_footer(text=_('Documentations provided by https://readthedocs.io'))
        await delete_with_emote(await ctx.send(_("Results for query **{0}** and documentation **{1}**".format(query, doc)), embed=embed))

def setup(bot):
    bot.add_cog(Doc(bot))
    bot.logger.info("Extension [doc] loaded successfully.")
