from __future__ import annotations

from typing import TYPE_CHECKING
from urllib import parse

import discord
from aiohttp import ClientSession
from bs4 import BeautifulSoup
from discord import app_commands
from discord.ext import commands

from utils.constants import BUG_CENTER_ID

if TYPE_CHECKING:
    from main import HelpCenterBot


class Doc(commands.Cog):
    def __init__(self, bot: HelpCenterBot) -> None:
        self.bot: HelpCenterBot = bot
        self.bot.tree.add_command(self.doc, guild=discord.Object(id=BUG_CENTER_ID))

    @app_commands.command(
        name="doc",
        description="Shows 4 or fewer links referring to a documentation on readthedocs.io :D",
    )
    @app_commands.describe(doc="The documentation you want to search for.", query="The search query.")
    # @checkers.authorized_channels()
    async def doc(self, inter: discord.Interaction, doc: str, query: str) -> None:
        url = "https://readthedocs.org/api/v2/search/"
        params = {
            "q": query,
            "project": doc,
            "version": "master",
        }
        async with ClientSession() as session:
            async with session.get(url, params=params) as r:
                json = await r.json()
                print(json)

        if not json.get("count"):
            return await inter.response.send_message("Nothing found.")

        embed = discord.Embed(
            title=f"{json['count']} Results (click here for a complete search)",
            url=f"{json['results'][0]['domain']}/en/stable/search.html?q={query}",
        )

        description = ""

        for result in json["results"][:4]:
            try:
                for block in result["blocks"][:2]:
                    description += (
                        f"\n[{block['title']}]({result['domain']}{result['path']}?highlight={query}#{block['id']})"
                    )
            except KeyError:
                pass

        embed.description = description

        embed.set_footer(text="Documentations provided by https://readthedocs.org")
        await inter.response.send_message("Results for query **{query}** and documentation **{doc}**", embed=embed)

    @doc.autocomplete("doc")
    async def doc_autocomplete(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        if len(current) < 4:
            return [app_commands.Choice(name="discord.py", value="discord.py")]

        async with ClientSession() as session:
            async with session.get(
                "https://readthedocs.org/search/?type=project&version=latest&q=" + parse.quote_plus(current)
            ) as r:
                result = await r.text()
        soup = BeautifulSoup(result, "html.parser")

        return [
            app_commands.Choice(name=value, value=value)
            for tag in soup.select(
                "#content > div > div > div > div.module > div > div.module-list > div > ul > li > p.module-item-title > a"
            )
            if (value := tag.get_text().split(" (")[0].strip()) or True
        ][:25]


async def setup(bot: HelpCenterBot) -> None:
    await bot.add_cog(Doc(bot))
    bot.logger.info("Extension [doc] loaded successfully.")
