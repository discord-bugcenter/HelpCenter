from __future__ import annotations

import asyncio
import re
from datetime import datetime, timedelta, timezone
from functools import partial
from typing import TYPE_CHECKING, NamedTuple, cast

import discord
from discord import app_commands, ui
from discord.ext import commands
from discord.utils import find, get
from typing_extensions import Self

from utils.constants import BUG_CENTER_ID, NEW_REQUEST_CHANNEL_ID, REQUEST_MESSAGE_ID, REQUESTS_CHANNEL_ID
from utils.types import Snowflake

if TYPE_CHECKING:
    from discord import RawThreadDeleteEvent, RawThreadUpdateEvent

    from main import HelpCenterBot

THREAD_ID_FROM_CONTENT = re.compile(r"\[.+\]\(https:\/\/discord\.com\/channels\/\d{18,20}\/(\d{18,20})\)")


class Request(NamedTuple):
    request_message_id: Snowflake
    thread_id: Snowflake
    user_id: Snowflake | None


class ThreadsHelpTickets(commands.Cog):
    def __init__(self, bot: HelpCenterBot) -> None:
        self.bot: HelpCenterBot = bot
        self._requests_channel_wb: discord.Webhook | None

        self.current_requests: list[Request] = []

        self.queue: asyncio.Queue[int] = asyncio.Queue(maxsize=1)

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        self.new_request_channel = cast(discord.TextChannel, self.bot.get_channel(NEW_REQUEST_CHANNEL_ID))
        self.requests_channel = cast(discord.TextChannel, self.bot.get_channel(REQUESTS_CHANNEL_ID))
        self.new_request_message = await self.new_request_channel.fetch_message(REQUEST_MESSAGE_ID)
        self._requests_channel_wb = get(await self.requests_channel.webhooks(), type=discord.WebhookType.incoming)
        self.create_thread_view = CreateThreadView(self)
        self.bot.add_view(self.create_thread_view, message_id=REQUEST_MESSAGE_ID)

        bug_center: discord.Guild = self.new_request_channel.guild
        self.event: discord.ScheduledEvent | None = find(
            lambda event: event.name.startswith("Demandes d'aide : "), bug_center.scheduled_events
        )
        self.event_disabled = False

        await self.update_message_overview()
        await self.update_overview()

    @commands.Cog.listener()
    async def on_interaction(self, inter: discord.Interaction) -> None:  # on_interaction should not be used, but..
        if inter.type == discord.InteractionType.application_command:
            return

        if (
            not inter.message
            or not inter.user
            or not inter.channel
            or not isinstance(inter.channel, discord.Thread)
            or not inter.data
            or not (custom_id := inter.data.get("custom_id"))
        ):
            return

        if custom_id.startswith("archive_help_thread_"):
            strategy = partial(inter.channel.edit, archived=True)
        else:
            return

        if custom_id.endswith(
            str(inter.user.id)
        ):  # or checkers.is_high_staff_check(self.bot, inter.user)[0]:  # TODO : work on checkers
            await strategy()
            await inter.response.defer(ephemeral=True)

    @commands.Cog.listener()
    async def on_raw_thread_update(self, payload: RawThreadUpdateEvent) -> None:
        print(self.requests_channel.threads)
        if payload.parent_id != REQUESTS_CHANNEL_ID:
            return
        await self.update_overview()

    @commands.Cog.listener()
    async def on_raw_thread_delete(self, payload: RawThreadDeleteEvent) -> None:
        if not payload.parent_id == REQUESTS_CHANNEL_ID:
            return
        await self.update_overview()

    @app_commands.command()
    @app_commands.guilds(BUG_CENTER_ID)
    async def toggle_event(self, inter: discord.Interaction) -> None:
        if self.event_disabled is False:
            if self.event is not None and self.event.status == discord.EventStatus.active:
                await self.event.end()
        else:
            await self.create_scheduled_event()
        self.event_disabled = not self.event_disabled
        await inter.response.send_message(
            content=f"Event {'disabled' if self.event_disabled else 'enabled'}", ephemeral=True
        )

    @property
    async def requests_channel_webhook(self) -> discord.Webhook:
        if not self._requests_channel_wb:
            self._requests_channel_wb = await self.requests_channel.create_webhook(name="Help Center Requests")
        return self._requests_channel_wb

    @staticmethod
    def get_thread_id_from_content(content: str) -> Snowflake | None:
        if result := THREAD_ID_FROM_CONTENT.match(content):
            return int(result.group(1))
        return None

    async def create_scheduled_event(self) -> discord.ScheduledEvent:
        bug_center: discord.Guild = self.new_request_channel.guild
        event = await bug_center.create_scheduled_event(
            name=f"Demandes d'aide : {len(self.new_request_channel.threads)}",
            start_time=datetime.now(timezone.utc) + timedelta(minutes=10),
            entity_type=discord.EntityType.external,
            location=f"<#{NEW_REQUEST_CHANNEL_ID}>",
            end_time=datetime.now(timezone.utc) + timedelta(days=365 * 3),
        )
        self.event = await event.start()
        return self.event

    def create_overview_embed(self) -> discord.Embed:
        embed = discord.Embed(
            color=discord.Color.blurple(),
            title="**Fils d'aide personnalisée **",
            description=(
                "Créez un fil pour recevoir de l'aide sur n'importe quel sujet informatique.\n"
                "Que ce soit de la programmation, un problème avec votre PC, etc...\n"
                "\n"
                "Voir <#926861260291711076> pour plus d'informations.\n"
                f"Voir <#{REQUESTS_CHANNEL_ID}> pour accéder à la liste des demandes."
            ),
        )
        return embed

    async def update_message_overview(self) -> None:
        embed = self.create_overview_embed()

        await self.new_request_message.edit(
            embed=embed,
            view=self.create_thread_view,
            content=(
                "__**Avant de poser une question :**__\n"
                " :ballot_box_with_check: avez-vous cherché sur Google ? https://google.com/search\n"
                " :ballot_box_with_check: avez-vous lu la documentation ?\n"
                "\n"
                "__**Lorsque vous posez une question :**__\n"
                " :ballot_box_with_check: ne demandez pas de l'aide, posez juste votre question. "
                "https://dontasktoask.com/\n"
                " :ballot_box_with_check: expliquez directement votre problème/objectif, ne passez pas par une "
                "situation similaire. https://xyproblem.info/\n"
                "\n"
                "__**Lorsque vous aidez quelqu'un :**__\n"
                "Le spoonfeed est interdit. Autrement dit, il est préférable d'indiquer à quelqu'un comment il peut "
                "résoudre son problème plutôt que de lui donner une réponse toute faite.\n"
                "\u200b"
            ),
        )

    async def update_overview(self) -> None:
        # edits are done using the state of discord when executed, so excessive edits are not necessary
        if self.queue.qsize() > 1:
            return

        await self.queue.put(0)

        for cached_request in self.current_requests.copy():
            if get(self.requests_channel.threads, id=cached_request.thread_id) is not None:
                continue
            await self.requests_channel.delete_messages((discord.Object(cached_request.request_message_id),))
            self.current_requests.remove(cached_request)

        async for message in self.requests_channel.history():
            if (thread_id := self.get_thread_id_from_content(message.content)) is None or get(
                self.requests_channel.threads, id=thread_id
            ) is None:
                await message.delete()
            elif get(self.current_requests, request_message_id=message.id) is None:
                self.current_requests.append(Request(request_message_id=message.id, thread_id=thread_id, user_id=None))

        for thread in self.requests_channel.threads:
            if get(self.current_requests, thread_id=thread.id) is not None:
                continue

            message = [m async for m in thread.history(oldest_first=True, limit=1)][0]
            user = message.mentions[0] if message.mentions else None

            if message.type is not discord.MessageType.recipient_add or user is None:
                username: str = "Utilisateur inconnu"
                avatar_url: str | None = None
            else:
                username = user.display_name
                avatar_url = user.display_avatar.url

            await (await self.requests_channel_webhook).send(
                content=f"[{thread.name}](https://discord.com/channels/{BUG_CENTER_ID}/{thread.id})",
                username=username,
                avatar_url=avatar_url,
                wait=True,
            )

        if not self.event_disabled:
            if len(self.new_request_channel.threads) == 0:
                if self.event is not None and self.event.status == discord.EventStatus.active:  # Duplicate condition...
                    await self.event.end()
                self.event = None
            elif self.event is not None and self.event.status == discord.EventStatus.active:
                self.event = await self.event.edit(
                    name=f"Demandes d'aide : {len(self.new_request_channel.threads)}",
                    entity_type=discord.EntityType.external,
                    location=f"<#{NEW_REQUEST_CHANNEL_ID}> (#{self.new_request_channel.name})",
                    end_time=datetime.now(timezone.utc) + timedelta(days=365 * 3),
                )
            else:
                await self.create_scheduled_event()

        async def release_queue_delayed():
            await asyncio.sleep(10)
            await self.queue.get()

        asyncio.create_task(release_queue_delayed())


class CreateThreadView(ui.View):
    def __init__(self, cog: ThreadsHelpTickets) -> None:
        """The view below the message in #ask-for-help, to create thread channels."""
        super().__init__(timeout=None)
        self.cog: ThreadsHelpTickets = cog

    @ui.button(label="Nouveau", custom_id="create_help_channel", emoji="➕", style=discord.ButtonStyle.blurple)
    async def create_help_channel(self, inter: discord.Interaction, button: ui.Button[Self]) -> None:
        if len(list(filter(lambda r: r.user_id == inter.user.id, self.cog.current_requests))) >= 5:
            await inter.response.send_message(
                ":x: Vous avez déjà atteins le nombre maximal de demandes. Archivez vos demandes précédentes.",
                ephemeral=True,
            )
        await inter.response.send_modal(CreateThreadModal(self.cog))


class CreateThreadModal(ui.Modal, title=""):
    thread_title = ui.TextInput[Self](label="tmp", placeholder="tmp", min_length=20, max_length=100)
    thread_content = ui.TextInput[Self](
        label="tmp", placeholder="tmp", style=discord.TextStyle.paragraph, min_length=50, max_length=2000
    )

    def __init__(self, cog: ThreadsHelpTickets) -> None:
        self.title = "Posez votre question"
        self.thread_title.label = "Sujet"
        self.thread_title.placeholder = "Décrivez succinctement votre problème."
        self.thread_content.label = "Contenue"
        self.thread_content.placeholder = (
            "Décrivez votre problème de manière détaillé. Soyez aussi claire que possible."
        )
        super().__init__()

        self.cog: ThreadsHelpTickets = cog

    async def on_submit(self, interaction: discord.Interaction) -> None:
        task = asyncio.create_task(
            self.cog.bot.wait_for(
                "message",
                check=lambda message: message.channel.id == REQUESTS_CHANNEL_ID
                and message.type == discord.MessageType.thread_created,
            )
        )

        thread = await self.cog.requests_channel.create_thread(
            name=f"{self.thread_title.value}",
            type=discord.ChannelType.public_thread,
            reason="HelpCenter help-thread system.",
        )

        async def additionnel_requests():
            await (await task).delete()

            view = ui.View()
            view.stop()
            view.add_item(ui.Button(label="Archive", custom_id=f"archive_help_thread_{interaction.user.id}"))

            await thread.add_user(interaction.user)
            message: discord.Message = await thread.send(content=self.thread_content.value, view=view)
            await message.pin()

            message = await (await self.cog.requests_channel_webhook).send(
                content=f"[{thread.name}](https://discord.com/channels/{BUG_CENTER_ID}/{thread.id})",
                username=interaction.user.display_name,
                avatar_url=interaction.user.display_avatar.url,
                wait=True,
            )
            self.cog.current_requests.append(Request(message.id, thread.id, interaction.user.id))

            await self.cog.update_overview()

        asyncio.create_task(additionnel_requests())
        await interaction.response.send_message(ephemeral=True, content=f"Un salon a été créé : <#{thread.id}>")


async def setup(bot: HelpCenterBot) -> None:
    await bot.add_cog(ThreadsHelpTickets(bot))
    bot.logger.info("Extension [threads_help_tickets] loaded successfully.")
