from __future__ import annotations

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

    async def create_scheduled_event(self) -> discord.ScheduledEvent:
        bug_center: discord.Guild = self.threads_channel.guild
        self.event = await bug_center.create_scheduled_event(
            name=f"Demandes d'aide : {len(self.threads_channel.threads)}",
            start_time=datetime.now(timezone.utc) + timedelta(minutes=10),
            entity_type=discord.EntityType.external,
            location=f"<#{ASK_CHANNEL_ID}>",
            end_time=datetime.now(timezone.utc) + timedelta(days=365 * 3),
        )
        await self.event.start()
        return self.event

    def update_overview_embed(self) -> None:
        embed = self.threads_overview_embed
        field_name = embed.fields[0].name

        if not self.threads_channel.threads:
            embed.fields[0].value = "*Aucune demande, hourra!*"
            return

        embed.clear_fields()
        field_contents = [""]
        i = 0

        for thread in self.threads_channel.threads:
            if len(field_contents[i]) + len(thread.name) + 100 > 1024:  # 100 is the length of the link etc...
                i += 1
                field_contents.append("")

            field_contents[i] += f" - [{thread.name}](https://discord.com/channels/{BUG_CENTER_ID}/{thread.id})\n"

        for i, content in enumerate(field_contents):
            embed.add_field(name=field_name if not i else "\u200b", value=content, inline=False)

    async def update_overview(self) -> None:
        self.update_overview_embed()
        await self.threads_overview_message.edit(
            embed=self.threads_overview_embed, view=self.create_thread_view, content=None
        )

        if self.event is not None and self.event.status == discord.EventStatus.active:
            await self.event.edit(
                name=f"Demandes d'aide : {len(self.threads_channel.threads)}",
                entity_type=discord.EntityType.external,
                location=f"<#{ASK_CHANNEL_ID}>",
                end_time=datetime.now(timezone.utc) + timedelta(days=365 * 3),
            )
        elif self.event_disabled is False:
            await self.create_scheduled_event()

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

        embed = discord.Embed(
            color=discord.Color.blurple(),
            title="**Fils d'aide personnalisée **",
            description=(
                "Créez un fil pour recevoir de l'aide sur n'importe quel sujet informatique.\n"
                "Que ce soit de la programmation, un problème avec votre PC, etc...\n"
            ),
        )
        embed.add_field(name="Liste des demandes en cours", value="*Aucune demande, hourra!*", inline=False)
        self.threads_overview_embed = embed

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
    async def on_thread_join(self, thread: discord.Thread) -> None:
        if not thread.parent_id == ASK_CHANNEL_ID or not thread.parent:
            return

        async for message in cast(discord.TextChannel, thread.parent).history():
            if message.id == thread.id:
                await message.delete()
                break

        await self.update_overview()

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

    @ui.button(label="Nouveau / New", custom_id="create_help_channel", emoji="➕", style=discord.ButtonStyle.blurple)
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
        await interaction.response.defer(ephemeral=True, thinking=True)
        channel = cast(discord.TextChannel, interaction.channel)

        thread = await channel.create_thread(
            name=f"{self.thread_title.value}",
            type=discord.ChannelType.public_thread,
            reason="HelpCenter help-thread system.",
        )

        view = ui.View()
        view.stop()
        view.add_item(ui.Button(label="Archive", custom_id=f"archive_help_thread_{interaction.user.id}"))

        await thread.add_user(interaction.user)
        await thread.send(content=self.thread_content.value, view=view)

        await self.cog.update_overview()
        await interaction.edit_original_response(content=f"Un salon a été créé : <#{thread.id}>")


async def setup(bot: HelpCenterBot) -> None:
    await bot.add_cog(ThreadsHelpTickets(bot))
    bot.logger.info("Extension [threads_help_tickets] loaded successfully.")
