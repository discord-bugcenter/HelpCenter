import os
import json

import discord
from discord.ext import commands
from discord_slash import SlashCommand, SlashContext
from schema import SchemaError

from cogs.utils.misc import tag_shema


class Tag(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.slash = SlashCommand(bot, override_type=True)

        tags_files = [os.path.join('ressources/tags/.', f) for f in os.listdir('ressources/tags/.') if os.path.isfile(os.path.join('ressources/tags/.', f))]
        self.tags = {}
        for path in tags_files:
            try:
                with open(path, "r", encoding='utf-8') as f:
                    loaded_tag = json.load(f)

                    try:
                        loaded_tag = tag_shema.validate(loaded_tag)
                    except SchemaError as e:
                        self.bot.logger.warning(f'The tag {path} is improper.\n{e}')
                        continue

                    self.tags[loaded_tag["name"]] = loaded_tag

            except Exception as e:
                print(e)
                self.bot.logger.warning(f"The tag {path} cannot be loaded")

        @self.slash.slash(name="tag")
        async def _tag(ctx: SlashContext, query):
            print(ctx.author)
            if query == "list":
                format_list = lambda tags_values: "\n".join([f"- `{tag.get('name')}` : {tag.get('description')}" for tag in tags_values])
                return await ctx.send(3, embeds=[
                    discord.Embed(
                        title="Vous pouvez utiliser ces tags :",
                        description=format_list(self.tags.values()),
                        color=discord.Color.from_rgb(54, 57, 63)
                    )
                ])
            tag = self.tags.get(query)

            if tag is None:
                return await ctx.send(content="Le tag n'a pas été trouvé, regardez `/tag list`")

            response = tag.get('response')

            embed = discord.Embed.from_dict(response.get("embed"))
            embed.color = discord.Color.from_rgb(54, 57, 63)
            embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.avatar_url)

            await ctx.send(  # content=response.get("content", ""),
                           embeds=[embed])

        print("Extension [tag] chargée avec succès.")

    def cog_unload(self):
        self.slash.remove()


def setup(bot):
    bot.add_cog(Tag(bot))
