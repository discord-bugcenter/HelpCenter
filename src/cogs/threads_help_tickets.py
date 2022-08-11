from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from functools import partial
from typing import TYPE_CHECKING, cast

import discord
from discord import app_commands, ui
from discord.ext import commands
from discord.utils import find
from typing_extensions import Self

from utils.constants import ASK_CHANNEL_ID, ASK_MESSAGE_ID, BUG_CENTER_ID

if TYPE_CHECKING:
    from main import HelpCenterBot


class ThreadsHelpTickets(commands.Cog):
    def __init__(self, bot: HelpCenterBot) -> None:
        self.bot: HelpCenterBot = bot
        self.bot.tree.add_command(self.toggle_event, guild=discord.Object(BUG_CENTER_ID))

        self.queue: asyncio.Queue[int] = asyncio.Queue(maxsize=1)

    async def create_scheduled_event(self) -> discord.ScheduledEvent:
        bug_center: discord.Guild = self.threads_channel.guild
        event = await bug_center.create_scheduled_event(
            name=f"Demandes d'aide : {len(self.threads_channel.threads)}",
            start_time=datetime.now(timezone.utc) + timedelta(minutes=10),
            entity_type=discord.EntityType.external,
            location=f"<#{ASK_CHANNEL_ID}>",
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
                "Voir <#926861260291711076> pour plus d'informations."
            ),
        )
        main_field_name = "Liste des demandes en cours"

        if not [t for t in self.threads_channel.threads if not t.archived]:
            return embed.add_field(name=main_field_name, value="*Aucune demande, hourra!*", inline=False)

        field_contents = [""]
        i = 0

        for thread in self.threads_channel.threads:
            if len(field_contents[i]) + len(thread.name) + 75 > 1024:  # 75 is the length of the link etc...
                i += 1
                field_contents.append("")

            field_contents[i] += f" - [{thread.name}](http://discord.com/channels/{BUG_CENTER_ID}/{thread.id})\n"

        for i, content in enumerate(field_contents):
            embed.add_field(name=main_field_name if not i else "\u200b", value=content, inline=False)
        return embed

    async def update_overview(self) -> None:
        # edits are done using the state of discord when executed, so excessive edits are not necessary
        if self.queue.qsize() > 1:
            return

        await self.queue.put(0)
        embed = self.create_overview_embed()

        await self.threads_overview_message.edit(
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

        if not self.event_disabled:
            if len(self.threads_channel.threads) == 0:
                if self.event is not None and self.event.status == discord.EventStatus.active:  # Duplicate condition...
                    await self.event.end()
                self.event = None
            elif self.event is not None and self.event.status == discord.EventStatus.active:
                self.event = await self.event.edit(
                    name=f"Demandes d'aide : {len(self.threads_channel.threads)}",
                    entity_type=discord.EntityType.external,
                    location=f"<#{ASK_CHANNEL_ID}>",
                    end_time=datetime.now(timezone.utc) + timedelta(days=365 * 3),
                )
            else:
                await self.create_scheduled_event()

        async def release_queue_delayed():
            await asyncio.sleep(10)
            await self.queue.get()

        asyncio.create_task(release_queue_delayed())

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        self.threads_channel = cast(discord.TextChannel, self.bot.get_channel(ASK_CHANNEL_ID))
        self.threads_overview_message = await self.threads_channel.fetch_message(ASK_MESSAGE_ID)
        self.create_thread_view = CreateThreadView(self)
        self.bot.add_view(self.create_thread_view, message_id=ASK_MESSAGE_ID)

        bug_center: discord.Guild = self.threads_channel.guild
        self.event: discord.ScheduledEvent | None = find(
            lambda event: event.name.startswith("Demandes d'aide : "), bug_center.scheduled_events
        )
        self.event_disabled = False

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
    async def on_thread_update(self, thread_before: discord.Thread, thread_after: discord.Thread) -> None:
        if not thread_before.parent_id == ASK_CHANNEL_ID or not thread_before.parent:
            return

        await self.update_overview()

    @commands.Cog.listener()
    async def on_thread_delete(self, thread: discord.Thread) -> None:
        if not thread.parent_id == ASK_CHANNEL_ID or not thread.parent:
            return

        await self.update_overview()

    @app_commands.command()
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


class CreateThreadView(ui.View):
    def __init__(self, cog: ThreadsHelpTickets) -> None:
        """The view below the message in #ask-for-help, to create thread channels."""
        super().__init__(timeout=None)
        self.cog: ThreadsHelpTickets = cog

    @ui.button(label="Nouveau", custom_id="create_help_channel", emoji="➕", style=discord.ButtonStyle.blurple)
    async def create_help_channel(self, inter: discord.Interaction, button: ui.Button[Self]) -> None:
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
        # await interaction.response.defer(ephemeral=True, thinking=True)
        channel = cast(discord.TextChannel, interaction.channel)

        task = asyncio.create_task(
            self.cog.bot.wait_for(
                "message",
                check=lambda message: message.channel.id == ASK_CHANNEL_ID
                and message.type == discord.MessageType.thread_created,
            )
        )

        thread = await channel.create_thread(
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

            await self.cog.update_overview()

        asyncio.create_task(additionnel_requests())
        await interaction.response.send_message(ephemeral=True, content=f"Un salon a été créé : <#{thread.id}>")


async def setup(bot: HelpCenterBot) -> None:
    await bot.add_cog(ThreadsHelpTickets(bot))
    bot.logger.info("Extension [threads_help_tickets] loaded successfully.")
