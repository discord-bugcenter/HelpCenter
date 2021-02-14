import re
import asyncio

import discord
from discord.ext import commands

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
            title=_("Use of /event")
        )

        for command in ctx.command.commands:
            embed.add_field(name=f"** • {command.name}**", value=f"`{command.usage}`", inline=False)

        await ctx.send(embed=embed)

    @event.command(
        name="participate",
        usage="/event participate {code}"
    )
    @commands.dm_only()
    async def participate(self, ctx, *, code):
        code_channel = self.bot.get_channel(self.code_channel_id)

        regex = re.search(r'(```)?(?:(\S*)\s)(\s*\S[\S\s]*)(?(1)```|)', code)
        if not regex:
            raise commands.CommandError(_('Your message must contains a block of code (with code language) ! *look `/tag discord markdown`*'))
        language, code = regex.groups()[1:]

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


def setup(bot):
    bot.add_cog(Event(bot))
