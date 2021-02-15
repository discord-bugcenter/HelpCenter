import re
import io
import asyncio
from functools import partial

import discord
from discord.ext import commands
import matplotlib.pyplot as plt
from matplotlib.ticker import StrMethodFormatter

from .utils import custom_errors
from .utils.i18n import use_current_gettext as _
from .utils import misc


class Event(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.code_channel_id = 810511403202248754

    @commands.group(
        name='event',
        description=_('Participate or get informations about an event.'),
        invoke_without_command=True
    )
    async def event(self, ctx):
        if ctx.guild and ctx.channel.id not in self.bot.test_channels_id:  # Not in dm or in tests channels
            raise custom_errors.NotAuthorizedChannels(ctx.channel, self.bot.test_channels_id)

        embed = discord.Embed(
            title=_("Use of /event"),
            color=misc.Color.grey_embed().discord
        )

        for command in ctx.command.commands:
            embed.add_field(name=f"** • {command.name} : {_(command.description)}**", value=f"`{command.usage}`", inline=False)

        await ctx.send(embed=embed)

    @event.command(
        name="participate",
        description=_("Participate to the contest !"),
        usage="/event participate {code}"
    )
    @commands.dm_only()
    async def participate(self, ctx, *, code):
        code_channel = self.bot.get_channel(self.code_channel_id)

        regex = re.search(r'(```)?(?:(\S*)\s)(\s*\S[\S\s]*)(?(1)```|)', code)
        if not regex:
            raise commands.CommandError(_('Your message must contains a block of code (with code language) ! *look `/tag discord markdown`*'))
        language, code = regex.groups()[1:]
        if len(code) > 1000:
            return await ctx.send(_("Looks like your code is too long! Try to remove the useless parts, the goal is to have a short and optimized code!"))

        old_participation = None
        async for message in code_channel.history(limit=None):
            if message.author.id != self.bot.user.id: continue
            if str(ctx.author.id) == message.embeds[0].fields[0].value.split('|')[0]:
                old_participation = message
                break

        valid_message = await ctx.send(_('**This is your participation :**\n\n') +
                                       _('`Language` -> `{0}`\n').format(language) +
                                       _('`Length` -> `{0}`\n').format(len(code)) +
                                       f'```{language}\n{code}```\n' +
                                       _('Do you want ot post it ? ✅ ❌'))

        self.bot.loop.create_task(misc.add_reactions(valid_message, ['✅', '❌']))

        try: reaction, user = await self.bot.wait_for('reaction_add', check=lambda react, usr: not usr.bot and react.message.id == valid_message.id and str(react.emoji) in ['✅', '❌'], timeout=120)
        except asyncio.TimeoutError: return

        if str(reaction.emoji) == '✅':
            embed = discord.Embed(
                title="Participation :",
                color=misc.Color.grey_embed().discord
            )
            embed.add_field(name='User', value=f'{ctx.author.id}|{ctx.author.mention}', inline=False)
            embed.add_field(name='Language', value=language, inline=True)
            embed.add_field(name='Length', value=str(len(code)), inline=True)
            embed.add_field(name='Code', value=f"```{language}\n{code}\n```", inline=False)

            if old_participation:
                await old_participation.edit(embed=embed)
                response = _("Your entry has been successfully modified !")
            else:
                await code_channel.send(embed=embed)
                response = _("Your entry has been successfully sent !")

            try: await ctx.send(response)
            except: pass
        else:
            try: await ctx.send(_('Cancelled'))
            except: pass  # prevent error if the user close his MP

    @event.command(
        name='cancel',
        description=_('Remove your participation from the contest'),
        usage="/event cancel"
    )
    async def cancel(self, ctx):
        if ctx.guild and ctx.channel.id not in self.bot.test_channels_id:  # Not in dm or in tests channels
            raise custom_errors.NotAuthorizedChannels(ctx.channel, self.bot.test_channels_id)

        code_channel = self.bot.get_channel(self.code_channel_id)

        old_participation = None
        async for message in code_channel.history(limit=None):
            if message.author.id != self.bot.user.id: continue
            if str(ctx.author.id) == message.embeds[0].fields[0].value.split('|')[0]:
                old_participation = message
                break

        if old_participation:
            await old_participation.delete()
            response = _('Your participation has been successfully deleted')
        else:
            response = _("You didn't participate !")

        await ctx.send(response)

    @event.command(
        name="stats",
        description=_("Get some stats about the current contest"),
        usage="/event stats"
    )
    async def stats(self, ctx):
        if ctx.guild and ctx.channel.id not in self.bot.test_channels_id:  # Not in dm or in tests channels
            raise custom_errors.NotAuthorizedChannels(ctx.channel, self.bot.test_channels_id)

        code_channel = self.bot.get_channel(self.code_channel_id)

        user_length = None
        list_of_length = []
        datas = {}
        async with ctx.channel.typing():
            async for message in code_channel.history(limit=None):
                if message.author.id != self.bot.user.id: continue
                if str(ctx.author.id) == message.embeds[0].fields[0].value.split('|')[0]:
                    user_length = int(message.embeds[0].fields[2].value)
                list_of_length.append(int(message.embeds[0].fields[2].value))
                language = message.embeds[0].fields[1].value
                datas.setdefault(language, 0)
                datas[language] += 1
        list_of_length.sort()

        embed = discord.Embed(
            title=_('Some informations...'),
            color=misc.Color.grey_embed().discord
        )
        embed.add_field(name=_("Number of participations :"), value=str(len(list_of_length)), inline=False)
        embed.add_field(name=_("Shortest participation (not tested) :"), value=str(min(list_of_length)), inline=False)
        if user_length:
            embed.add_field(name=_('Your position :'), value=str(list_of_length.index(user_length)+1))
        embed.set_image(url="attachment://graph.png")

        fn = partial(self.create_graph_bars, datas)
        final_buffer = await self.bot.loop.run_in_executor(None, fn)

        file = discord.File(filename="graph.png", fp=final_buffer)

        await ctx.channel.send(embed=embed, file=file)

    @staticmethod
    def create_graph_bars(datas):
        fig, ax = plt.subplots()
        langs = datas.keys()
        values = datas.values()
        ax.bar(langs, values,
               color=misc.Color(10, 100, 255, 0.5).mpl,
               edgecolor=misc.Color(10, 100, 255).mpl,
               linewidth=5)

        ax.yaxis.set_major_formatter(StrMethodFormatter('{x:,.0f}'))  # No decimal places
        ax.set_yticks(range(1, max(values) + 1))
        ax.set_title(_("Breakdown by languages used."))
        buff = io.BytesIO()
        fig.savefig(buff)
        buff.seek(0)

        return buff


def setup(bot):
    bot.add_cog(Event(bot))
