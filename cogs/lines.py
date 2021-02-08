import re

import discord
from discord.ext import commands

from .utils.misc import delete_with_emote
from .utils import checkers


class Lines(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(
        name='lines',
        usage='/lines \\`\\`\\`{code}\\`\\`\\`',
        description='Ajoute le numéro des lignes au code'
    )
    @checkers.authorized_channels()
    async def lines(self, ctx):
        result = re.search(r'```(?:(\S*)\n)?(\s*\S[\S\s]*)```', ctx.message.content)

        if not result:
            raise commands.CommandError('Vous devez mettre un block de code dans votre message ! *Regardez `/tag discord code block`*')

        numbered_code = '\n'.join(f'{i:>3} | {line}' for i, line in enumerate(result.group(2).splitlines()))
        if len(numbered_code) > 1950:
            numbered_code = numbered_code[:1950] + '\netc...'

        response_message = await ctx.send(f'Code numéroté de {ctx.author} :\n' +
                                          '```' + (result.group(1) or '') + '\n' +
                                          numbered_code +
                                          '\n```')
        await ctx.message.delete()
        await delete_with_emote(ctx, response_message)


def setup(bot):
    bot.add_cog(Lines(bot))
    bot.logger.info("Extension [lines] loaded successfully.")

