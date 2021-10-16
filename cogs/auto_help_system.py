import asyncio
from typing import TYPE_CHECKING
from urllib import parse
from functools import partial

import discord
from discord import ui
from discord.ext import commands

from .utils.i18n import use_current_gettext as _
from .utils import checkers

if TYPE_CHECKING:
    from main import HelpCenterBot
    from .utils import Context

ASK_CHANNEL_ID = 870023524985761822
ASK_MESSAGE_ID = 870032630119276645


class AutoHelpSystem(commands.Cog):
    def __init__(self, bot: 'HelpCenterBot') -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        self.bot.add_view(CreateHelpChannelButton(self.bot), message_id=ASK_MESSAGE_ID)

    @commands.command(hidden=True)
    @checkers.is_high_staff()
    async def init_help(self, ctx: 'Context') -> None:
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

        embed.set_footer(text="⬇ Cliquez / Click")

        await ctx.send(embed=embed,
                       view=CreateHelpChannelButton(self.bot))

    @commands.Cog.listener()
    async def on_interaction(self, inter: discord.Interaction) -> None:  # on_interaction should not be used, but..
        if not isinstance(inter, discord.MessageInteraction):
            return

        if not inter.message or not inter.user or not inter.channel or not isinstance(inter.channel, discord.Thread):
            return

        custom_id = inter.data.get('custom_id')
        if not custom_id:
            return

        if custom_id.startswith('archive_help_thread_'):
            strategy = partial(inter.channel.edit, archived=True)
        elif custom_id.startswith('delete_help_thread_'):
            strategy = inter.channel.delete
        else:
            return

        if custom_id.endswith(str(inter.user.id)) or checkers.is_high_staff_check(self.bot, inter.user)[0]:
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


class CreateHelpChannelButton(ui.View):
    def __init__(self, bot: 'HelpCenterBot') -> None:
        """The view below the message in #ask-for-help, to create thread channels."""
        super().__init__(timeout=None)
        self.bot = bot

    @ui.button(label="Nouveau / New", custom_id='create_help_channel', emoji="➕", style=discord.ButtonStyle.blurple)
    async def create_help_channel(self, __: ui.Button, inter: discord.MessageInteraction) -> None:
        if not inter.guild or not inter.user or not isinstance(inter.channel, discord.TextChannel):
            return

        member = inter.guild.get_member(inter.user.id) or await inter.guild.fetch_member(inter.user.id)
        await inter.channel.set_permissions(member, send_messages=True)

        await self.bot.set_actual_language(inter.user)  # define bot langage for the next text

        content = _("**Give a title to your request.** \n"
                    "*Do not send your whole problem, just a very concise description with maximum context. (Language, OS, library used...) *\n\n"
                    "> Example: \"[Python - Discord.py] Is it possible to kick any one of a server with its id?\"")
        await inter.response.send_message(content, ephemeral=True)

        try:
            message = await self.bot.wait_for("message", check=lambda msg: msg.channel.id == inter.channel_id and msg.author.id == inter.user.id, timeout=300)
        except asyncio.TimeoutError:
            await inter.channel.set_permissions(member, overwrite=None)
            return

        while len(message.content) > 200:
            await self.bot.set_actual_language(inter.user)  # define bot langage for the next text
            await inter.edit_original_message(content=_("{0}\n\n"
                                                        "⚠ **This is not your full message of the request, the title must be short (less than 100 characters)**.\n\n"
                                                        "Your current request:```\n{1}\n```").format(content, message.content)
                                              )
            await message.delete()

            try:
                message = await self.bot.wait_for("message", check=lambda msg: msg.channel.id == inter.channel_id and msg.author.id == inter.user.id, timeout=300)
            except asyncio.TimeoutError:
                await inter.channel.set_permissions(member, overwrite=None)
                return

        if message.type is discord.MessageType.thread_created:  # The user can created a thread by him-self
            embed = discord.Embed()
            if not isinstance((channel := inter.guild.get_channel(message.id)), discord.Thread):
                return
            else:
                thread: discord.Thread = channel
        else:
            await message.delete()

            thread = await inter.channel.create_thread(
                name=f"{message.content[:100]}",
                auto_archive_duration=1440,
                type=discord.ChannelType.public_thread,
                reason="HelpCenter help-thread system."
            )

            await inter.channel.set_permissions(member, overwrite=None)
            await thread.add_user(inter.user)

        view = ui.View()
        view.stop()
        view.add_item(ui.Button(label=_("Archive"), custom_id=f"archive_help_thread_{inter.user.id}"))
        view.add_item(ui.Button(label=_("Delete"), custom_id=f"delete_help_thread_{inter.user.id}"))

        await self.bot.set_actual_language(inter.user)  # redefine the language, if he was long to write his answer

        embed = discord.Embed(
            color=discord.Color.yellow(),
            title=message.content
        )
        embed.add_field(
            name=_("Ask your question."),
            value=_("Be as clear as possible, remember to send code if there is, or screens highlighting the problem! \n\n"
                    "**⚠️ Do not share passwords, bot tokens... if anyone in demand, warn a staff member** ⚠️"),
            inline=False
        )

        embed.set_footer(text=_("⬇ click to archive the thread"))

        await self.bot.set_actual_language(inter.user)
        embed.add_field(
            name=_('How to ask a question ?'),
            value=_(":ballot_box_with_check: have you searched on Google ? [Search](https://google.com/search?q={0})\n"
                    ":ballot_box_with_check: have you read the doc ?\n"
                    ":ballot_box_with_check: don't ask to ask, just ask. https://dontasktoask.com/\n"
                    ":ballot_box_with_check: asking about your attempted solution rather than your actual problem. https://xyproblem.info/").format(
                        parse.quote_plus(" ".join(word[:50] for word in message.content.split(' ')[:32]))
                    ),
            inline=False
        )

        await thread.send(embed=embed, view=view)


def setup(bot: HelpCenterBot) -> None:
    bot.add_cog(AutoHelpSystem(bot))
