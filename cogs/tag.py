import os
from os import path
import json
import asyncio
from difflib import SequenceMatcher

import discord
from discord.ext import commands
from schema import SchemaError

from .utils.misc import tag_shema
from .utils import checkers, misc


class Tag(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

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

        print("Extension [tag] chargée avec succès.")

    @commands.command(
        name="tag",
        usage="/tag <category> (<tag_name>|'list')",
        description="Obtenir de l'aide rapidement"
    )
    @checkers.authorized_channels()
    async def _tag(self, ctx, category=None, *, query=None):
        await ctx.message.delete()  # suppression de la commande
        category_tags = self.tags.get(category)  # category_tags correspond a un dictionnaire avec plusieurs commandes

        if category_tags is None and category is not None:
            similors = ((name, SequenceMatcher(None, name, category).ratio()) for name in self.tags.keys())
            similors = sorted(similors, key=lambda couple: couple[1], reverse=True)

            if similors[0][1] > 0.8:
                category = similors[0][0]  # nom de la catégorie
                category_tags = self.tags.get(category)

        if category_tags is None:
            format_list = lambda keys: "\n".join([f"- `{key}`" for key in keys])
            embed = discord.Embed(
                title="Catégorie non trouvée. Essayez parmi :",
                description=format_list(self.tags.keys()),
                color=discord.Color.from_rgb(47, 49, 54)
            )
            embed.set_footer(text=ctx.command.usage)
            message = await ctx.send(embed=embed)
            return await misc.delete_with_emote(ctx, message)

        if query is None or query == "list":
            format_list = lambda tags_values: "\n".join([f"- `{tag.get('name')}` : {tag.get('description')}" for tag in tags_values])
            message = await ctx.channel.send(embed=discord.Embed(title=f"Voici les tags de la catégorie `{category}` :",
                                                                 description=format_list(category_tags.values()),
                                                                 color=discord.Color.from_rgb(47, 49, 54))
                                             )
            return await misc.delete_with_emote(ctx, message)

        tag = category_tags.get(query)

        if tag is None:
            similors = ((name, SequenceMatcher(None, name, query).ratio()) for name in category_tags.keys())
            similors = sorted(similors, key=lambda couple: couple[1], reverse=True)

            if similors[0][1] > 0.8:
                query = similors[0][0]  # nom du tag
                tag = category_tags.get(query)
            else:
                similar_text = f"voulez vous-vous dire `{similors[0][0]}` ? Sinon "
                return await ctx.send(f"Le tag n'a pas été trouvé, {similar_text if similors[0][1] > 0.5 else ''}regardez `/tag list`", delete_after=10)

        message = None
        response = tag.get('response')
        choice = response.get('choice')
        if choice:
            choice_keys = list(choice.keys())  # Un dict n'a pas d'ordre fixe, alors on se base sur 1 seule liste
            reactions = ['0️⃣', '1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '9️⃣']
            message = await ctx.send("__Choisissez la cible :__\n"+'\n'.join([f'{reactions[i]} - `{choice_name}`' for i, choice_name in enumerate(choice_keys)]))
            self.bot.loop.create_task(misc.add_reactions(message, reactions[:len(choice_keys)]))

            try:
                reaction, _ = await self.bot.wait_for('reaction_add', timeout=120, check=lambda react, usr: str(react.emoji) in reactions[:len(choice_keys)] and usr.id == ctx.author.id and react.message.id == message.id)
            except TimeoutError:
                return await message.delete()

            try: await message.clear_reactions()
            except: pass
            response = choice.get(choice_keys[reactions.index(str(reaction.emoji))])

        embed = discord.Embed.from_dict(response.get("embed"))
        embed.color = discord.Color.from_rgb(47, 49, 54)
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.avatar_url)

        text = f'/tag {category} {query}'
        url = discord.Embed.Empty
        creator = await self.bot.fetch_user(response.get('author')) if response.get('author') else None
        if creator:
            text += f' * par {creator.name}#{creator.descriminator}',
            url = creator.avatar_url
        embed.set_footer(
            text=text,
            icon_url=url
        )

        if message: await message.edit(embed=embed, content="")
        else: message = await ctx.channel.send(embed=embed)

        await misc.delete_with_emote(ctx, message)


def setup(bot):
    bot.add_cog(Tag(bot))
