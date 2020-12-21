import os
import json
import asyncio
from difflib import SequenceMatcher

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
            if query == "list":
                format_list = lambda tags_values: "\n".join([f"- `{tag.get('name')}` : {tag.get('description')}" for tag in tags_values])
                await ctx.send(5)
                return await ctx.channel.send(embed=discord.Embed(title="Vous pouvez utiliser ces tags :",
                                                                  description=format_list(self.tags.values()),
                                                                  color=discord.Color.from_rgb(54, 57, 63))
                                              )
            tag = self.tags.get(query)

            if tag is None:
                similors = ((name, SequenceMatcher(None, name, query).ratio()) for name in self.tags.keys())
                similors = sorted(similors, key=lambda couple: couple[1], reverse=True)

                similar_text = f"voulez vous-vous dire `{similors[0][0]}` ? Sinon "
                return await ctx.send(content=f"Le tag n'a pas été trouvé, {similar_text if similors[0][1] > 0.8 else ''}regardez `/tag list`", complete_hidden=True)

            response = tag.get('response')

            embed = discord.Embed.from_dict(response.get("embed"))
            embed.color = discord.Color.from_rgb(54, 57, 63)
            embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.avatar_url)

            await ctx.send(5)
            message = await ctx.channel.send(embed=embed)
            await message.add_reaction("🗑️")

            try:
                await self.bot.wait_for("reaction_add", timeout=120,
                                        check=lambda reaction, user: str(reaction.emoji) == "🗑️" and reaction.message.channel.id == ctx.channel.id and user.id == ctx.author.id)
            except asyncio.TimeoutError:
                try: await message.clear_reactions()
                except: pass
                return
            else:
                await message.delete()

        print("Extension [tag] chargée avec succès.")

    def cog_unload(self):
        self.slash.remove()


def setup(bot):
    bot.add_cog(Tag(bot))
