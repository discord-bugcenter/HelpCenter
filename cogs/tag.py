import os
from os import path
import json
from difflib import SequenceMatcher

import discord
from discord.ext import commands
from schema import SchemaError

from .utils.misc import tag_shema
from .utils import checkers, misc
from .utils.i18n import use_current_gettext as _


class Tag(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        tags_folder = {
            category: {
                    path.splitext(tag_name)[0]: path.join(category_path, tag_name) for tag_name in os.listdir(category_path)
                } for category in os.listdir('ressources/tags/') if path.isdir(category_path := path.join('ressources/tags/', category))
        }

        def complete_values(obj, ref=None):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if value == "*" and ref:
                        obj[key] = ref[key]
                    else:
                        obj[key] = complete_values(value, ref=ref[key] if ref else ref)
            elif isinstance(obj, list) and all(isinstance(sub_obj, dict) for sub_obj in obj):
                for i, sub_obj in enumerate(obj):
                    if i == 0 and not ref: continue
                    obj[i] = complete_values(obj[i], ref=ref[i] if ref else obj[0])

            return obj

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

                        self.tags[category_name][(loaded_tag[0] if isinstance(loaded_tag, list) else loaded_tag)["name"]] = complete_values(loaded_tag)

                except Exception as e:
                    print(e)
                    self.bot.logger.warning(f"The tag {tag_path} cannot be loaded")

    @commands.command(
        name="tag",
        usage="/tag <category> (<tag_name>|'list')",
        description="Obtenir de l'aide rapidement"
    )
    @checkers.authorized_channels()
    async def _tag(self, ctx, category=None, *, query=None):
        category_tags = self.tags.get(category)  # category_tags is a dict with categories of the tag

        if category_tags is None and category is not None:
            similors = ((name, SequenceMatcher(None, name, category).ratio()) for name in self.tags.keys())
            similors = sorted(similors, key=lambda couple: couple[1], reverse=True)

            if similors[0][1] > 0.8:
                category = similors[0][0]  # category name
                category_tags = self.tags.get(category)

        if category_tags is None:  # if the given category isn't ~= or == to any category
            format_list = lambda keys: "\n".join([f"- `{key}`" for key in keys])
            embed = discord.Embed(
                title=_("Category not found. Try among :"),
                description=format_list(self.tags.keys()),
                color=discord.Color.from_rgb(47, 49, 54)
            )
            embed.set_footer(text=ctx.command.usage)
            message = await ctx.send(embed=embed)
            return await misc.delete_with_emote(ctx, message)

        def get_tag_lang(tag):
            if isinstance(tag, dict):  # there is just one lang
                return tag
            found_tag = discord.utils.find(lambda in_tag: in_tag.get('lang') == self.bot.get_member_lang(ctx.author), tag)
            return found_tag or tag[0]

        if query is None or query == "list":  # if no tag name was given, or the tag name is "list"
            format_list = lambda tags_values: "\n".join([f"- `{get_tag_lang(tag).get('name')}` : {get_tag_lang(tag).get('description')}" for tag in tags_values])
            message = await ctx.channel.send(embed=discord.Embed(title=_("Here are the tags from the `{0}` category :").format(category),
                                                                 description=format_list(category_tags.values()),
                                                                 color=discord.Color.from_rgb(47, 49, 54))
                                             )
            return await misc.delete_with_emote(ctx, message)

        selected_tag = category_tags.get(query) or discord.utils.find(lambda tag: (aliases := get_tag_lang(tag).get('aliases')) and query in aliases, category_tags.values())

        if selected_tag is None:  # given tag name not in tags or aliases
            similors = ((name, SequenceMatcher(None, name, query).ratio()) for name in category_tags.keys())
            similors = sorted(similors, key=lambda couple: couple[1], reverse=True)

            if similors[0][1] > 0.8:
                query = similors[0][0]  # tag name
                selected_tag = category_tags.get(query)
            else:
                similar_text = _("do you mean `{0}` ? Otherwise ").format(similors[0][0])
                return await ctx.send(_("Tag not found, {0}look `/tag list`").format(similar_text if similors[0][1] > 0.5 else ''), delete_after=10)

        selected_tag = get_tag_lang(selected_tag)

        message = None
        response = selected_tag.get('response')
        choices = response.get('choices')
        if choices:
            reactions = ['0️⃣', '1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '9️⃣']
            message = await ctx.send(_("__Choose the target :__\n")+'\n'.join([f"{reactions[i]} - `{choice['choice_name']}`" for i, choice in enumerate(choices)]))
            self.bot.loop.create_task(misc.add_reactions(message, reactions[:len(choices)]))

            try:
                reaction, __ = await self.bot.wait_for('reaction_add', timeout=120,
                                                       check=lambda react, usr: str(react.emoji) in reactions[:len(choices)] and usr.id == ctx.author.id and react.message.id == message.id)
            except TimeoutError:
                return await message.delete()

            try: await message.clear_reactions()
            except: pass
            response = choices[reactions.index(str(reaction.emoji))]

        embed = discord.Embed.from_dict(response.get("embed"))
        embed.color = discord.Color.from_rgb(47, 49, 54)
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.avatar_url)

        text = f'/tag {category} {query}'
        url = self.bot.user.avatar_url
        embed.set_footer(
            text=text,
            icon_url=url
        )

        if message: await message.edit(embed=embed, content="")
        else: message = await ctx.channel.send(embed=embed)

        try: await ctx.message.delete()  # delete the trigger message (the command)
        except: pass
        try: await misc.delete_with_emote(ctx, message)
        except: pass


def setup(bot):
    bot.add_cog(Tag(bot))
    bot.logger.info("Extension [tag] loaded successfully.")
