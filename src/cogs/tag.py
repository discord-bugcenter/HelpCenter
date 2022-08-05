from __future__ import annotations

import asyncio
import io
import os
from typing import TYPE_CHECKING, Any

import aiohttp
import discord
import tomli  # TODO: use builtin with python 3.11
from discord import Embed, File, app_commands
from discord.ext import commands, tasks
from pydantic import AnyHttpUrl, BaseModel, Extra, Field, root_validator

from utils.constants import BUG_CENTER_ID
from utils.custom_errors import CustomError

if TYPE_CHECKING:
    from main import HelpCenterBot


REPOSITORY_TOKEN = os.environ["GITHUB_REPOSITORY_TOKEN"]


# Payload objects


class TagEmbedFieldPayload(BaseModel, extra=Extra.forbid):
    name: str
    value: str
    inline: bool = False


class TagEmbedPayload(BaseModel, extra=Extra.forbid):
    title: str
    description: str | None = None
    image: AnyHttpUrl | None = None
    thumbnail: AnyHttpUrl | None = None
    fields: list[TagEmbedFieldPayload] = Field(default_factory=list)


class TagAttachmentsPayload(BaseModel, extra=Extra.forbid):
    filename: str
    description: str | None = None
    url: AnyHttpUrl


class TagPayload(BaseModel, extra=Extra.forbid):
    name: str
    description: str
    content: str | None = None

    embeds: list[TagEmbedPayload] = Field(default_factory=list)
    attachments: list[TagAttachmentsPayload] = Field(default_factory=list)

    @root_validator()
    def validate_attachments(cls, values: dict[str, Any]) -> dict[str, Any]:
        if not values["content"] and not values["embeds"]:
            raise ValueError("Tag must have either content or embeds, or both.")
        return values


# Tag object parsed


class Tag:
    __slots__ = ("name", "description", "content", "_embeds", "_attachments", "attachments", "category")

    def __init__(self, data: TagPayload, category: str) -> None:
        self.name: str = data.name
        self.description: str = data.description
        self.content: str | None = data.content
        self._embeds: list[TagEmbedPayload] = data.embeds
        self._attachments: list[TagAttachmentsPayload] = data.attachments
        self.category: str = category

    async def get_attachments(self) -> None:
        self.attachments: list[File] = []
        for attachment_payload in self._attachments:
            async with aiohttp.ClientSession() as session:
                async with session.get(attachment_payload.url) as response:
                    buffer = io.BytesIO(await response.read())
                    buffer.seek(0)

                    self.attachments.append(
                        File(
                            buffer,
                            attachment_payload.filename,
                            description=attachment_payload.description,
                        )
                    )

    @property
    def embeds(self) -> list[Embed]:
        embeds: list[Embed] = []

        for embed_payload in self._embeds:
            embed = Embed(title=embed_payload.title, description=embed_payload.description)
            for field in embed_payload.fields:
                embed.add_field(name=field.name, value=field.value, inline=field.inline)
            if embed_payload.image:
                embed.set_image(url=embed_payload.image)
            if embed_payload.thumbnail:
                embed.set_thumbnail(url=embed_payload.thumbnail)

            embeds.append(embed)

        return embeds


class TagCog(commands.Cog):
    def __init__(self, bot: HelpCenterBot) -> None:
        """Tag command allow you to search for help in pre-saved topics."""
        self.bot: HelpCenterBot = bot
        self.last_sha_commit: str | None = None
        self.tags: dict[str, list[Tag]] = {}  # A dict which looks like {"category_name": [Tag, ...]}}
        self.bot.tree.add_command(self._tag, guild=discord.Object(id=BUG_CENTER_ID))
        self.bot.tree.add_command(self._force_resync, guild=discord.Object(id=BUG_CENTER_ID))

        headers = {"Authorization": f"token {REPOSITORY_TOKEN}"}
        self.session = aiohttp.ClientSession(headers=headers)
        self.check_for_changes.start()

    async def cog_unload(self) -> None:
        await self.session.close()

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        await self.fetch_tags()

    @tasks.loop(minutes=1)
    async def check_for_changes(self) -> None:
        async with self.session.get("https://api.github.com/repos/discord-bugcenter/tags/commits") as r:
            raw_data = await r.json()
            last_sha = raw_data[0]["sha"]

        if self.last_sha_commit is not None and self.last_sha_commit != last_sha:
            self.last_sha_commit = last_sha
            await asyncio.sleep(300)  # Raws are cached for 5 minutes, so we need to wait before fetching again
            await self.fetch_tags()
        else:
            self.last_sha_commit = last_sha

    async def fetch_tags(self) -> None:
        self.tags = {}
        async with self.session.get("https://api.github.com/repositories/472858036/contents/src") as r:
            raw_categories = await r.json()

        for raw_category in raw_categories:
            category_tags: list[Tag] = []
            category = raw_category["name"]

            async with self.session.get(raw_category["url"]) as r:
                raw_tags = await r.json()

            for raw_tag in raw_tags:
                try:
                    async with self.session.get(raw_tag["download_url"]) as r:
                        tag_payload = TagPayload.parse_obj(tomli.loads(await r.text()))
                    tag = Tag(tag_payload, category)

                    if any(tag.name == _tag.name for _tag in category_tags):
                        raise ValueError(f"{tag.name} ({raw_tag['path']}) is already a tag")

                    await tag.get_attachments()
                    category_tags.append(tag)
                    self.bot.logger.debug(f"Tag {tag.name} from {tag.category} ({raw_tag['path']}) successfully loaded")

                except Exception as e:
                    self.bot.logger.warning(f'The tag {raw_tag["path"]} cannot be loaded. Error : {e}')
                    continue

            self.tags[category] = category_tags

    @app_commands.command(name="force_resync")
    async def _force_resync(self, inter: discord.Interaction) -> None:
        await self.fetch_tags()

    @app_commands.command(name="tag", description="Envoyer les messages répétitifs.")
    @app_commands.describe(tag_identifier="La catégorie que vous souhaitez sélectionner")
    @app_commands.rename(tag_identifier="nom")
    # @checkers.authorized_channels()
    async def _tag(self, inter: discord.Interaction, tag_identifier: str) -> None:
        """The tag command, that will do a research into saved tags, using the category and the query gave."""
        try:
            category_name, tag_name = tag_identifier.split(".")
            if (tmp := discord.utils.get(self.tags[category_name], name=tag_name)) is None:
                raise ValueError(f"{tag_name} is not a tag in {category_name}")
            tag: Tag = tmp
        except (ValueError, KeyError):
            raise CustomError("Select a tag from the list.")

        embeds = tag.embeds
        if embeds:
            embeds[-1].set_footer(text="Les tags sont fait par la communauté, n'hésitez pas à en proposer.")
            for embed in embeds:
                embed.color = discord.Color.from_rgb(47, 49, 54)

        await inter.response.send_message(content=tag.content, embeds=embeds, files=tag.attachments)

    @_tag.autocomplete("tag_identifier")
    async def category_autocompleter(self, inter: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        def search_tags(search_text: str) -> list[Tag]:
            """
            Return a list of tags that match the search text.
            Tags whose search_text matches the beginning of the name are placed first,
            Tags whose search_text is contained in the name are placed next,
            Tags whose search_text matches the beginning of the category are placed last.
            """
            tags_begin_match: set[Tag] = set()
            tags_contained_match: set[Tag] = set()
            tags_category_match: set[Tag] = set()

            for category, tags_list in self.tags.items():
                for tag in tags_list:
                    if tag.name.startswith(search_text):
                        tags_begin_match.add(tag)
                    elif search_text in tag.name:
                        tags_contained_match.add(tag)

                if category.startswith(search_text):
                    tags_category_match |= set(tags_list)

            # tags_category_match can contain duplicates, so we remove them
            tags_category_match = tags_category_match - tags_begin_match - tags_contained_match

            def sort_key(tag: Tag) -> tuple[str, str]:
                return tag.category, tag.name

            tags = (
                sorted(tags_begin_match, key=sort_key)
                + sorted(tags_contained_match, key=sort_key)
                + sorted(tags_category_match, key=sort_key)
            )
            return tags[:25]

        return [
            app_commands.Choice(name=f"{tag.name} [{tag.category}]", value=".".join((tag.category, tag.name)))
            for tag in search_tags(current)
        ]


async def setup(bot: HelpCenterBot) -> None:
    await bot.add_cog(TagCog(bot))
    bot.logger.info("Extension [tag] loaded successfully.")
