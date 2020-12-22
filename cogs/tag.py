import os
from os import path
import json
import asyncio
from difflib import SequenceMatcher

import discord
from discord.ext import commands
from discord_slash import SlashCommand, SlashContext
from schema import SchemaError

from .utils.misc import tag_shema
from .utils import checkers, misc


class Tag(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.slash = SlashCommand(bot, override_type=True)

        tags_folder = {
            category: {
                    path.splitext(tag_name)[0]: path.join(path.join('ressources/tags/', category), tag_name) for tag_name in os.listdir(path.join('ressources/tags', category)) if path.isdir(path.join('ressources/tags', category))
                } for category in os.listdir('ressources/tags/') if os.path.isdir(os.path.join('ressources/tags/', category))
        }

        self.tags = {}
        for category_name, tags_infos in tags_folder.items():
            self.tags[category_name] = {}
            for tag_name, tag_path in tags_infos.items():
                try:
                    with open(tag_path, "r", encoding='utf-8') as f:
                        loaded_tag = json.load(f)

                        try:
                            loaded_tag = tag_shema.validate(loaded_tag)
                        except SchemaError as e:
                            self.bot.logger.warning(f'The tag {tag_name} from category {category_name} is improper.\n{e}')
                            continue

                        self.tags[category_name][loaded_tag["name"]] = loaded_tag

                except Exception as e:
                    print(e)
                    self.bot.logger.warning(f"The tag {tag_path} cannot be loaded")

        @self.slash.slash(name="tag")
        @checkers.authorized_channels
        async def _tag(ctx: SlashContext, category, query):
            category_tags = self.tags.get(category)

            if query == "list":
                format_list = lambda tags_values: "\n".join([f"- `{tag.get('name')}` : {tag.get('description')}" for tag in tags_values])
                await ctx.send(5)
                return await ctx.channel.send(embed=discord.Embed(title=f"Voici les tags de la catégorie `{category}` :",
                                                                  description=format_list(category_tags.values()),
                                                                  color=discord.Color.from_rgb(47, 49, 54))
                                              )
            tag = category_tags.get(query)

            if tag is None:
                similors = ((name, SequenceMatcher(None, name, query).ratio()) for name in category_tags.keys())
                similors = sorted(similors, key=lambda couple: couple[1], reverse=True)

                similar_text = f"voulez vous-vous dire `{similors[0][0]}` ? Sinon "
                return await ctx.send(content=f"Le tag n'a pas été trouvé, {similar_text if similors[0][1] > 0.8 else ''}regardez `/tag list`", complete_hidden=True)

            message = None
            response = tag.get('response')
            choice = response.get('choice')
            if choice:
                choice_keys = list(choice.keys())  # Un dict n'a pas d'ordre fixe, alors on se base sur 1 seule liste
                reactions = ['0️⃣', '1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '9️⃣']
                await ctx.send(5)
                message = await ctx.channel.send("__Choisissez la cible :__\n"+'\n'.join([f'{reactions[i]} - `{choice_name}`' for i, choice_name in enumerate(choice_keys)]))
                self.bot.loop.create_task(misc.add_reactions(message, reactions[:len(choice_keys)]))

                try:
                    reaction, _ = await self.bot.wait_for('reaction_add', timeout=120, check=lambda react, usr: str(react.emoji) in reactions[:len(choice_keys)] and usr.id == ctx.author.id and react.message.id == message.id)
                except TimeoutError:
                    return await message.delete()

                await message.clear_reactions()
                response = choice.get(choice_keys[reactions.index(str(reaction.emoji))])

            embed = discord.Embed.from_dict(response.get("embed"))
            embed.color = discord.Color.from_rgb(47, 49, 54)
            embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.avatar_url)

            if message: await message.edit(embed=embed, content="")
            else: message = await ctx.channel.send(embed=embed)

            await message.add_reaction("🗑️")

            try:
                await self.bot.wait_for("reaction_add", timeout=120,
                                        check=lambda react, usr: str(react.emoji) == "🗑️" and react.message.channel.id == ctx.channel.id and usr.id == ctx.author.id)
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
