from typing import Union, TypedDict, Optional, cast
import json
import asyncio
import os

import aiohttp
import discord
from discord.utils import get
from discord.ext import commands, tasks
from discord import app_commands, ui

from cogs.utils.types import Person

from .utils.misc import tag_schema
from .utils.constants import BUG_CENTER_ID
from .utils import misc  # , checkers
from .utils.i18n import _
from main import HelpCenterBot

REPOSITORY_TOKEN = os.environ["GITHUB_REPOSITORY_TOKEN"]

ResponseChoices = TypedDict('ResponseChoices', content=str, embed=dict, choice_name=str)
Response = TypedDict('Response', content=str, embed=dict, choices=list[ResponseChoices])


class Tag:
    def __init__(self, data):
        self.lang = data.get('lang') or 'fr_FR'
        self.name: str = data["name"]
        self.description: str = data['description']
        self.response: Response = data['response']

    @classmethod
    def parse_tag(cls, data: Union[dict, list]) -> list['Tag']:
        if isinstance(data, list):
            return [cls(json_tag) for json_tag in cls.complete_values(data)]
        else:  # isinstance(data, dict)
            return [cls(cls.complete_values(data))]

    @staticmethod
    def complete_values(obj: Union[dict, list, str], ref: Optional[Union[dict, list, str]] = None):
        """This function will fill values where there is a * in the tag.json based on the corresponding field located above"""
        if isinstance(obj, dict):
            for key, value in obj.items():
                if value == "*" and ref:
                    obj[key] = ref[key]
                else:
                    obj[key] = Tag.complete_values(value, ref=ref[key] if ref else ref)
        elif isinstance(obj, list) and all(isinstance(sub_obj, dict) for sub_obj in obj):
            for i in range(len(obj)):
                if i == 0 and not ref:
                    continue
                obj[i] = Tag.complete_values(obj[i], ref=ref[i] if ref else obj[0])

        return obj

    def __str__(self):
        return f"<Tag name={self.name} lang={self.lang} description={self.description}>"


class TagCog(commands.Cog):
    def __init__(self, bot: 'HelpCenterBot') -> None:
        """Tag command allow you to search for help in pre-saved topics."""
        self.bot = bot
        self.last_sha_commit: Optional[str] = None
        self.tags: dict[str, dict[str, list[Tag]]] = {}  # A dict which looks like {"category_name": {"tag_name": [Tag]}}
        self.bot.tree.add_command(self._tag, guild=discord.Object(id=BUG_CENTER_ID))
        self.bot.tree.add_command(self._force_resync, guild=discord.Object(id=BUG_CENTER_ID))

        headers = {
            'Authorization': f'token {REPOSITORY_TOKEN}'
        }
        self.session = aiohttp.ClientSession(headers=headers)
        self.check_for_changes.start()

    async def cog_unload(self) -> None:
        await self.session.close()

    @commands.Cog.listener()
    async def on_ready(self):
        await self.fetch_tags()

    @tasks.loop(minutes=1)
    async def check_for_changes(self):
        async with self.session.get("https://api.github.com/repos/discord-bugcenter/tags/commits") as r:
            raw_data = await r.json()
            last_sha = raw_data[0]['sha']

        if self.last_sha_commit is not None and self.last_sha_commit != last_sha:
            self.last_sha_commit = last_sha
            await asyncio.sleep(300)  # Raws are cached for 5 minutes, so we need to wait before fetching again
            await self.fetch_tags()
        else:
            self.last_sha_commit = last_sha

    async def fetch_tags(self):
        self.tags = {}
        async with self.session.get("https://api.github.com/repositories/472858036/contents/src") as r:
            raw_categories = await r.json()

        for raw_category in raw_categories:
            self.tags[raw_category['name']] = {}

            async with self.session.get(raw_category['url']) as r:
                raw_tags = await r.json()

            for raw_tag in raw_tags:
                try:
                    async with self.session.get(raw_tag['download_url']) as r:
                        json_tag: Union[dict, list] = json.loads(await r.text())

                    assert isinstance(json_tag := tag_schema.validate(json_tag), list) or isinstance(json_tag, dict)

                    parsed_tags = Tag.parse_tag(json_tag)
                    self.tags[raw_category['name']][parsed_tags[0].name] = parsed_tags
                except Exception as e:
                    HelpCenterBot.logger.warning(f'The tag {raw_tag["path"]} from category cannot be loaded. Error : {e}')
                    continue

    @app_commands.command(name="force_resync")
    async def _force_resync(self, inter: discord.Interaction):
        await self.fetch_tags()

    @app_commands.command(name="tag", description="Envoyer les messages répétitifs.")
    @app_commands.describe(category_name="La catégorie que vous souhaitez selectionner",
                           tag_name="Le tag que vous souhaitez envoyer")
    @app_commands.rename(category_name="category", tag_name="tag")
    # @app_commands.choices(category=[app_commands.Choice(name=category_name, value=category_name) for category_name in tags.keys()])
    # @checkers.authorized_channels()
    async def _tag(self, inter: discord.Interaction, category_name: str, tag_name: str) -> None:
        """The tag command, that will do a research into savec tags, using the category and the query gived."""
        if category_name not in self.tags:
            return await inter.response.send_message(_("This category doesn't exist.", inter), ephemeral=True)
        category = self.tags[category_name]

        if tag_name == "list" or tag_name not in category:
            def format_category(_category: dict[str, list[Tag]]) -> str:
                translated_tags = [get(tag_langs, lang=inter.locale.value) or tag_langs[0] for tag_langs in _category.values()]

                return "\n".join([f"- `{tag.name}` : {tag.description}" for tag in translated_tags])

            await inter.response.send_message(embed=discord.Embed(title=_("Here are the tags from the `{0}` category :").format(category_name),
                                                                  description=format_category(category),
                                                                  color=misc.Color.grey_embed().discord)
                                              )
            # await misc.delete_with_emote(self.bot, inter.user, await inter.original_message())
            return

        tag_langs = category[tag_name]

        tag: Tag = get(tag_langs, lang=inter.locale.value) or tag_langs[0]

        choices = tag.response.get('choices')
        kwargs = {}
        if choices:
            kwargs['embed'] = embed = discord.Embed.from_dict(choices[0]['embed'])
            kwargs['view'] = MultipleChoicesView(self.bot, inter.user, choices, tag_name, category_name)
        else:
            kwargs['embed'] = embed = discord.Embed.from_dict(tag.response["embed"])

        embed.colour = misc.Color.grey_embed().discord
        embed.set_author(name=inter.user.display_name, icon_url=inter.user.display_avatar.url)
        embed.set_footer(
            text=f'/tag {category_name} {tag_name}',
            icon_url=self.bot.user.display_avatar.url  # type: ignore
        )

        await inter.response.send_message(**kwargs)
        # await misc.delete_with_emote(self.bot, inter.user, await inter.original_message())

    @_tag.autocomplete('category_name')
    async def category_autocompleter(self, inter: discord.Interaction, current: str):
        return [app_commands.Choice(name=category, value=category) for category in self.tags.keys() if current in category]

    @_tag.autocomplete('tag_name')
    async def tag_autocompleter(self, inter: discord.Interaction, current: str):
        if inter.namespace['category'] not in self.tags.keys():
            return [app_commands.Choice(name=_('You must first fill the category option.', inter), value='')]
        return [app_commands.Choice(name=tag_name, value=tag_name) for tag_name in self.tags[inter.namespace['category']].keys() if current in tag_name] + [app_commands.Choice(name='list', value='list')]


class MultipleChoicesView(discord.ui.View):
    def __init__(self, bot: HelpCenterBot, author: 'Person', choices: list[ResponseChoices], tag_name: str, category_name: str):
        self.bot = bot
        self.author = author
        self.choices = choices
        self.tag_name = tag_name
        self.category_name = category_name

        super().__init__()

        cast(ui.Select, self.children[0]).options = [
            discord.SelectOption(label=choice['choice_name'], default=i == 0) for i, choice in enumerate(self.choices)
        ]

        # self.selector = discord.ui.Select(custom_id='multiple_choices_tag', options=[
        #     discord.SelectOption(label=choice['choice_name'], default=i == 0) for i, choice in enumerate(self.choices)
        # ])
        # self.selector.callback = _ViewCallback(MultipleChoicesView.selector_callback, self, self.selector)
        # self.add_item(self.selector)

    async def interaction_check(self, inter: discord.Interaction) -> bool:
        if inter.user.id == self.author.id:
            return True
        await inter.response.defer(ephemeral=True)
        return False

    @ui.select(custom_id='multiple_choices_tag')
    async def selector_callback(self, inter: discord.Interaction, select: ui.Select) -> None:
        values = cast(list[str], select.values)
        response = cast(ResponseChoices, discord.utils.find(lambda choice: choice['choice_name'] == values[0], self.choices))

        embed = discord.Embed.from_dict(response["embed"])
        embed.colour = misc.Color.grey_embed().discord
        embed.set_author(name=inter.user.display_name, icon_url=inter.user.display_avatar.url)
        embed.set_footer(
            text=f'/tag {self.category_name} {self.tag_name}',
            icon_url=self.bot.user.display_avatar.url  # type: ignore
        )

        for option in select.options:
            option.default = option.label == values[0]

        try:
            await inter.response.edit_message(embed=embed, view=self)
        except discord.HTTPException:
            self.stop()


async def setup(bot: 'HelpCenterBot'):
    await bot.add_cog(TagCog(bot))
    bot.logger.info("Extension [tag] loaded successfully.")
