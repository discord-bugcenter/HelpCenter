import re
import io
import asyncio
from functools import partial
from datetime import datetime

import discord
from discord.ext import commands
import matplotlib.pyplot as plt
from matplotlib.ticker import StrMethodFormatter

from .utils import custom_errors
from .utils.i18n import use_current_gettext as _
from .utils import misc

RE_DESC_EVENT_DATE = re.compile(r'event-date : (\d{,2})/(\d{,2})/(\d{4})')
RE_DESC_EVENT_STATE = re.compile(r'event-state : (\S+)')
CODE_CHANNEL_ID = 810511403202248754

LANGAGE_COMPREHENSION = {
    'py': 'python3',
    'python': 'python3',
    'python3': 'python3',
    'js': 'javascript',
    'javascript': 'javascript',
    'cpp': 'cpp',
    'c++': 'cpp',
    'bash': 'bash',
    'c': 'c',
    'csharp': 'csharp',
    'go': 'go',
    'haskell': 'haskell',
    'java': 'java',
    'kotlin': 'kotlin',
    'node': 'javascript',
    'perl': 'perl',
    'php': 'php',
    'ruby': 'ruby',
    'rust': 'rust',
    'swift': 'swift',
    'typescript': 'javascript'
}


def event_not_closed():
    async def inner(ctx):
        code_channel = ctx.bot.get_channel(CODE_CHANNEL_ID)
        state = RE_DESC_EVENT_STATE.search(code_channel.topic).group(1)

        if state == 'closed':
            await ctx.bot.set_actual_language(ctx.author)
            await ctx.send(_('There is no event right now, sorry !'), delete_after=5)
            return False

        return True

    return commands.check(inner)


def event_not_ended():
    async def inner(ctx):
        code_channel = ctx.bot.get_channel(CODE_CHANNEL_ID)
        state = RE_DESC_EVENT_STATE.search(code_channel.topic).group(1)

        if state == 'ended':
            await ctx.bot.set_actual_language(ctx.author)
            await ctx.send(_('The event is ended, sorry !'), delete_after=5)
            return False

        return True

    return commands.check(inner)


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
    @event_not_ended()
    @event_not_closed()
    async def participate(self, ctx, *, code):
        code_channel = self.bot.get_channel(self.code_channel_id)
        day, month, year = RE_DESC_EVENT_DATE.search(code_channel.topic).groups()

        regex = re.search(r'(```)?(?:(\S*)\s)(\s*\S[\S\s]*)(?(1)```|)', code)
        if not regex:
            raise commands.CommandError(_('Your message must contains a block of code (with code language) ! *look `/tag discord markdown`*'))
        language, code = regex.groups()[1:]
        if len(code) > 1000:
            return await ctx.send(_("Looks like your code is too long! Try to remove the useless parts, the goal is to have a short and optimized code!"))
        if language.lower() not in LANGAGE_COMPREHENSION.keys():
            return await ctx.send(_('Your language seems not be valid for the event.'))

        old_participation = None
        async for message in code_channel.history(limit=None, after=datetime(int(year), int(month), int(day))):
            if message.author.id != self.bot.user.id: continue
            if str(ctx.author.id) == message.embeds[0].fields[0].value.split('|')[0]:
                old_participation = message
                break

        valid_message = await ctx.send(_('**This is your participation :**\n\n') +
                                       _('`Language` -> `{0}`\n').format(LANGAGE_COMPREHENSION[language.lower()]) +
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
            embed.add_field(name='Language', value=LANGAGE_COMPREHENSION[language.lower()], inline=True)
            embed.add_field(name='Length', value=str(len(code)), inline=True)
            embed.add_field(name='Date', value=str(datetime.now().isoformat()), inline=False)
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
    @event_not_ended()
    @event_not_closed()
    async def cancel(self, ctx):
        if ctx.guild and ctx.channel.id not in self.bot.test_channels_id:  # Not in dm or in tests channels
            raise custom_errors.NotAuthorizedChannels(ctx.channel, self.bot.test_channels_id)

        code_channel = self.bot.get_channel(self.code_channel_id)
        day, month, year = RE_DESC_EVENT_DATE.search(code_channel.topic).groups()

        old_participation = None
        async for message in code_channel.history(limit=None, after=datetime(int(year), int(month), int(day))):
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
    @event_not_closed()
    async def stats(self, ctx):
        if ctx.guild and ctx.channel.id not in self.bot.test_channels_id:  # Not in dm or in tests channels
            raise custom_errors.NotAuthorizedChannels(ctx.channel, self.bot.test_channels_id)

        code_channel = self.bot.get_channel(self.code_channel_id)
        day, month, year = RE_DESC_EVENT_DATE.search(code_channel.topic).groups()

        user_length = None
        list_of_length = []
        datas = {}
        async with ctx.channel.typing():
            async for message in code_channel.history(limit=None, after=datetime(int(year), int(month), int(day))):
                if message.author.id != self.bot.user.id: continue
                length = int(message.embeds[0].fields[2].value)
                language = message.embeds[0].fields[1].value

                if str(ctx.author.id) == message.embeds[0].fields[0].value.split('|')[0]:
                    user_length = length
                    user_language = language

                list_of_length.append(length)
                datas.setdefault(language, [])
                datas[language].append(length)

        list_of_length.sort()
        [v.sort() for v in datas.values()]

        embed = discord.Embed(
            title=_('Some informations...'),
            color=misc.Color.grey_embed().discord
        )
        embed.add_field(name=_("Number of participations :"), value=str(len(list_of_length)), inline=False)
        if user_length:
            embed.add_field(name=_('Your global position :'), value=str(list_of_length.index(user_length)+1))
            embed.add_field(name=_('Your position by language :'), value=str(datas[user_language].index(user_length)+1))
        embed.set_image(url="attachment://graph.png")

        fn = partial(self.create_graph_bars, datas, _("Breakdown by languages used."))
        final_buffer = await self.bot.loop.run_in_executor(None, fn)

        file = discord.File(filename="graph.png", fp=final_buffer)

        await ctx.channel.send(embed=embed, file=file)

    @staticmethod
    def create_graph_bars(datas, title):  # title in arguments because translations doesn't work in a separated thread
        fig, ax = plt.subplots()
        langs = datas.keys()
        values = [len(v) for v in datas.values()]
        ax.bar(langs, values,
               color=misc.Color(10, 100, 255, 0.5).mpl,
               edgecolor=misc.Color(10, 100, 255).mpl,
               linewidth=5)

        ax.yaxis.set_major_formatter(StrMethodFormatter('{x:,.0f}'))  # No decimal places
        ax.set_yticks(range(1, max(values) + 1))
        ax.set_title(title)
        buff = io.BytesIO()
        fig.savefig(buff)
        buff.seek(0)
        del fig

        return buff


def setup(bot):
    bot.add_cog(Event(bot))
