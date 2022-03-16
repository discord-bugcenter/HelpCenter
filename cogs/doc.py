from typing import TYPE_CHECKING
from urllib import parse

import discord
from discord.ext import commands
from aiohttp import ClientSession
from bs4 import BeautifulSoup

from .utils import checkers
from .utils.misc import delete_with_emote
from .utils.i18n import use_current_gettext as _
from .utils.constants import BUG_CENTER_ID

if TYPE_CHECKING:
    from main import HelpCenterBot


async def doc_autocompleter(inter: discord.ApplicationCommandInteraction, user_input: str):  # This is spamming and will maybe get removed.
    if len(user_input) < 4:
        return ['discord.py', 'discord']
    async with ClientSession() as session:
        async with session.get("https://readthedocs.org/search/?type=project&version=latest&q=" + parse.quote_plus(user_input)) as r:
            result = await r.text()
    soup = BeautifulSoup(result, 'html.parser')
    return [tag.get_text().split(' (')[0].strip() for tag in soup.select('#content > div > div > div > div.module > div > div.module-list > div > ul > li > p.module-item-title > a')][:25]


class Doc(commands.Cog):
    def __init__(self, bot: 'HelpCenterBot'):
        self.bot = bot

    @commands.slash_command(
        name='doc',
        usage='/doc {query}',
        description=_('Shows 4 or fewer links referring to a documentation on readthedocs.io :D'),
        guild_ids=[BUG_CENTER_ID]
    )
    @checkers.authorized_channels()
    async def doc(self,
                  inter: discord.ApplicationCommandInteraction,
                  doc: str = commands.Param(autocomp=doc_autocompleter),
                  query: str = commands.Param()):

        url = 'https://readthedocs.org/api/v2/search/'
        params = {
            'q': query,
            'project': doc,
            'version': 'latest',
        }
        async with ClientSession() as session:
            async with session.get(url, params=params) as r:
                json = await r.json()

        if not json.get('count'):
            return await inter.response.send_message('Not found.')

        embed = discord.Embed(title=_("{} Results (click here for a complete search)".format(json['count'])),
                              description="",
                              url="{}/en/stable/search.html?q={}".format(json['results'][0]['domain'], query))

        for result in json['results'][:4]:
            try:
                for block in result['blocks'][:2]:
                    embed.description += f"\n[{block['title']}]({result['domain']}{result['path']}?highlight={query}#{block['id']})"
            except KeyError:
                # embed.description += f"\n[{result['title']}]({result['domain']}{result['path']}?highlight={query}#{block['id']})"
                pass

        embed.set_footer(text=_('Documentations provided by https://readthedocs.org'))
        await inter.response.send_message(_("Results for query **{0}** and documentation **{1}**".format(query, doc)), embed=embed)
        await delete_with_emote(self.bot, inter.author, await inter.original_message())


def setup(bot: 'HelpCenterBot'):
    bot.add_cog(Doc(bot))
    bot.logger.info("Extension [doc] loaded successfully.")
