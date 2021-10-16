from typing import Union, TypedDict
import os
from os import path
import json

import discord
from disnake.utils import get
from disnake.ext import commands
from schema import SchemaError

from cogs.utils.types import Person

from .utils.misc import tag_schema
from .utils.constants import BUG_CENTER_ID
from .utils import checkers, misc
from .utils.i18n import use_current_gettext as _
from main import HelpCenterBot


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
    def complete_values(obj: Union[dict, list, str], ref: Union[dict, list, str] = None):
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


tags_paths: dict[str, dict] = {}  # A dict which looks like {"category_name": {"tag_name": "/path/to/tag.json"}}  (path is "/category_name/tag_name.json")
for category_name in os.listdir('ressources/tags/'):
    if not path.isdir(category_path := path.join('ressources/tags/', category_name)):
        continue

    category: dict[str, str] = {path.splitext(tag_name)[0]: path.join(category_path, tag_name) for tag_name in os.listdir(category_path)}

    tags_paths[category_name] = category

tags: dict[str, dict[str, list[Tag]]] = {}  # A dict which looks like {"category_name": {"tag_name": [Tag]}}
for category_name, tags_infos in tags_paths.items():
    tags[category_name] = {}
    for tag_name, tag_path in tags_infos.items():
        try:
            with open(tag_path, "r", encoding='utf-8') as f:
                json_tag: Union[dict, list] = json.load(f)

                try:
                    assert isinstance(tmp := tag_schema.validate(json_tag), list) or isinstance(tmp, dict)
                    json_tag = tmp
                except SchemaError as e:
                    HelpCenterBot.logger.warning(f'The tag {tag_name} from category {category_name} is improper.\n{e}')
                    continue

                parsed_tags = Tag.parse_tag(json_tag)

                tags[category_name][parsed_tags[0].name] = parsed_tags

        except Exception:
            HelpCenterBot.logger.warning(f"The tag {tag_path} cannot be loaded")


async def tag_autocompleter(inter: discord.ApplicationCommandInteraction, user_input: str):
    if not inter.filled_options.get('category'):
        return [_('You must first fill the category option.')]
    return [tag_name for tag_name in tags[inter.filled_options['category']].keys() if user_input in tag_name] + ['list']


class TagCog(commands.Cog):
    def __init__(self, bot: 'HelpCenterBot') -> None:
        """Tag command allow you to search for help in pre-saved topics."""
        self.bot = bot

    @commands.slash_command(
        name="tag",
        usage="/tag <category> (<tag_name>|'list')",
        description=_("Send redundant help messages."),
        guild_ids=[BUG_CENTER_ID]
    )
    @checkers.authorized_channels()
    async def _tag(self,
                   inter: discord.ApplicationCommandInteraction,
                   category_name: str = commands.Param(name='category', desc="La catégorie que vous souhaitez selectionner", choices=list(tags.keys())),
                   tag_name: str = commands.Param(name='tag', desc="Le tag que vous souhaitez envoyer", autocomp=tag_autocompleter)) -> None:
        """The tag command, that will do a research into savec tags, using the category and the query gived."""
        category = tags[category_name]
        user_lang = self.bot.get_user_language(inter.author)

        if tag_name == "list":
            def format_category(_category: dict[str, list[Tag]]) -> str:
                translated_tags = []
                for tag_langs in _category.values():
                    translated_tags.append(get(tag_langs, lang=user_lang))

                return "\n".join([f"- `{tag.name}` : {tag.description}" for tag in translated_tags])

            await inter.response.send_message(embed=discord.Embed(title=_("Here are the tags from the `{0}` category :").format(category_name),
                                                                  description=format_category(category),
                                                                  color=misc.Color.grey_embed().discord)
                                              )
            await misc.delete_with_emote(self.bot, inter.author, await inter.original_message())
            return

        tag_langs = category.get(tag_name)
        if not tag_langs:
            return

        tag: Tag = get(tag_langs, lang=user_lang) or tag_langs[0]

        choices = tag.response.get('choices')
        kwargs = {}
        if choices:
            kwargs['embed'] = embed = discord.Embed.from_dict(choices[0].get('embed'))
            kwargs['view'] = MultipleChoicesView(self.bot, inter.author, choices, tag_name, category_name)
        else:
            kwargs['embed'] = embed = discord.Embed.from_dict(tag.response.get("embed"))

        embed.colour = misc.Color.grey_embed().discord
        embed.set_author(name=inter.author.display_name, icon_url=inter.author.display_avatar.url)
        embed.set_footer(
            text=f'/tag {category_name} {tag_name}',
            icon_url=self.bot.user.display_avatar.url
        )

        await inter.response.send_message(**kwargs)
        await misc.delete_with_emote(self.bot, inter.author, await inter.original_message())


class MultipleChoicesView(discord.ui.View):
    def __init__(self, bot: HelpCenterBot, author: 'Person', choices: list[ResponseChoices], tag_name: str, category_name: str):
        self.bot = bot
        self.author = author
        self.choices = choices
        self.tag_name = tag_name
        self.category_name = category_name

        super().__init__()

        self.selector = discord.ui.Select(custom_id='multiple_choices_tag', options=[
            discord.SelectOption(label=choice['choice_name'], default=i == 0) for i, choice in enumerate(self.choices)
        ])
        self.selector.callback = self.selector_callback
        self.add_item(self.selector)

    async def interaction_check(self, interaction: discord.MessageInteraction) -> bool:
        if interaction.author.id == self.author.id:
            return True
        await interaction.response.defer(ephemeral=True)
        return False

    async def selector_callback(self, inter: discord.MessageInteraction):
        values = inter.values
        assert values is not None
        response = discord.utils.find(lambda choice: choice['choice_name'] == values[0], self.choices)
        assert response is not None

        embed = discord.Embed.from_dict(response.get("embed"))
        embed.colour = misc.Color.grey_embed().discord
        embed.set_author(name=inter.author.display_name, icon_url=inter.author.display_avatar.url)
        embed.set_footer(
            text=f'/tag {self.category_name} {self.tag_name}',
            icon_url=self.bot.user.display_avatar.url
        )

        for option in self.selector.options:
            option.default = option.label == values[0]

        try:
            await inter.response.edit_message(embed=embed, view=self)
        except discord.HTTPException:
            self.stop()


def setup(bot: 'HelpCenterBot'):
    bot.add_cog(TagCog(bot))
    bot.logger.info("Extension [tag] loaded successfully.")
