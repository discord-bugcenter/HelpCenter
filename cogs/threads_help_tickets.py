from typing import TYPE_CHECKING, cast
from functools import partial

import discord
from discord import ui
from discord.ext import commands

from .utils.i18n import _
from .utils import Context  # , checkers

if TYPE_CHECKING:
    from main import HelpCenterBot

ASK_CHANNEL_ID = 870023524985761822
ASK_MESSAGE_ID = 870032630119276645


class ThreadsHelpTickets(commands.Cog):
    def __init__(self, bot: 'HelpCenterBot') -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        self.bot.add_view(CreateThreadView(self.bot), message_id=ASK_MESSAGE_ID)

    # @commands.command(hidden=True)
    # @checkers.is_high_staff()
    async def init_help(self, ctx: Context) -> None:
        embed = discord.Embed(color=discord.Color.blurple())
        embed.add_field(
            name=":flag_fr: **Fils d\'aide personnalisée**",
            value=("Créez un fil pour recevoir de l\'aide sur n\'importe quel sujet informatique.\n"
                   "Que ce soit de la programmation, un problème avec votre PC, etc...\n"),
            inline=False
        )
        embed.add_field(
            name=":flag_us: **Personalized help threads**",
            value=("Create a thread to receive help on any digital subject.\n"
                   "It can be about programming, hardware...\n"),
            inline=False
        )

        await ctx.send(embed=embed,
                       view=CreateThreadView(self.bot))

    @commands.Cog.listener()
    async def on_interaction(self, inter: discord.Interaction) -> None:  # on_interaction should not be used, but..
        if inter.type == discord.InteractionType.application_command:
            return

        if (not inter.message or
                not inter.user or
                not inter.channel or
                not isinstance(inter.channel, discord.Thread) or
                not inter.data or
                not (custom_id := inter.data.get('custom_id'))):
            return

        if custom_id.startswith('archive_help_thread_'):
            strategy = partial(inter.channel.edit, archived=True)
        # elif custom_id.startswith('delete_help_thread_'):
        #     strategy = inter.channel.delete
        else:
            return

        if custom_id.endswith(str(inter.user.id)):  # or checkers.is_high_staff_check(self.bot, inter.user)[0]:  # TODO : work on checkers
            await strategy()
            await inter.response.defer(ephemeral=True)

    @commands.Cog.listener()
    async def on_thread_update(self, thread_before: discord.Thread, thread_after: discord.Thread) -> None:
        if not thread_before.parent_id == ASK_CHANNEL_ID or not thread_before.parent or (thread_before.archived and not thread_after.archived):
            return

        async for message in thread_before.parent.history():
            if message.id == thread_after.id:
                await message.delete()
                break

    @commands.Cog.listener()
    async def on_thread_delete(self, thread: discord.Thread) -> None:
        if not thread.parent_id == ASK_CHANNEL_ID or not thread.parent:
            return

        async for message in thread.parent.history():
            if message.id == thread.id:
                await message.delete()
                break


class CreateThreadView(ui.View):
    def __init__(self, bot: 'HelpCenterBot') -> None:
        """The view below the message in #ask-for-help, to create thread channels."""
        super().__init__(timeout=None)
        self.bot = bot

    @ui.button(label="Nouveau / New", custom_id='create_help_channel', emoji="➕", style=discord.ButtonStyle.blurple)
    async def create_help_channel(self, __: ui.Button, inter: discord.Interaction) -> None:
        await inter.response.send_modal(CreateThreadModal(inter))


class CreateThreadModal(ui.Modal, title=''):
    thread_title = ui.TextInput(label="tmp", placeholder="tmp", min_length=20, max_length=100)
    thread_content = ui.TextInput(label="tmp", placeholder="tmp", style=discord.TextStyle.paragraph, min_length=100, max_length=2000)

    def __init__(self, inter: discord.Interaction):
        self.title = _("Ask your question", inter)
        self.thread_title.label = _("Summary", inter)
        self.thread_title.placeholder = _("Briefly present the subject of your question.", inter)
        self.thread_content.label = _("Content", inter)
        self.thread_content.placeholder = _("Explain your question in detail. Be as clear as possible", inter)
        super().__init__()

    async def on_submit(self, inter: discord.Interaction):
        channel = cast(discord.TextChannel, inter.channel)

        thread = await channel.create_thread(
            name=f"{self.thread_title.value}",
            type=discord.ChannelType.public_thread,
            reason="HelpCenter help-thread system.",
        )

        embed = discord.Embed(
            color=discord.Color.yellow(),
            title=self.thread_title
        )
        embed.set_author(name=inter.user.display_name, icon_url=inter.user.display_avatar.url)
        embed.set_footer(text=_("⬇ click to archive the thread", inter))

        view = ui.View()
        view.stop()
        view.add_item(ui.Button(label=_("Archive"), custom_id=f"archive_help_thread_{inter.user.id}"))
        #  view.add_item(ui.Button(label=_("Delete"), custom_id=f"delete_help_thread_{inter.user.id}"))

        await thread.send(embed=embed, view=view)
        await thread.add_user(inter.user)
        await thread.send(content=self.thread_content.value)

        await inter.response.send_message(_('A thread has been created : <#{}>', inter).format(thread.id), ephemeral=True)


async def setup(bot: 'HelpCenterBot') -> None:
    await bot.add_cog(ThreadsHelpTickets(bot))
