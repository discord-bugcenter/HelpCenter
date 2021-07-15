import re

from discord.ext import commands

from main import HelpCenterBot
from .utils.misc import delete_with_emote
from .utils import checkers
from .utils.i18n import use_current_gettext as _


class Lines(commands.Cog):
    def __init__(self, bot: HelpCenterBot) -> None:
        self.bot = bot

    @commands.command(
        name='lines',
        usage='/lines \\`\\`\\`{code}\\`\\`\\`',
        description=_('Add the lines number to your code.')
    )
    @checkers.authorized_channels()
    async def lines(self, ctx: commands.Context) -> None:
        """A command that add number before each lines."""
        result = re.search(r'```(?:(\S*)\n)?(\s*\S[\S\s]*)```', ctx.message.content)

        if not result:
            raise commands.CommandError(_('Your message must contains a block of code ! *look `/tag discord code block`*'))

        numbered_code = '\n'.join(f'{i+1:>3} | {line}' for i, line in enumerate(result.group(2).splitlines()))
        if len(numbered_code) > 1950:
            numbered_code = numbered_code[:1950] + '\netc...'

        response_message = await ctx.send(_('Numbered code of {ctx.author} :\n').format(**locals()) +
                                          '```' + (result.group(1) or '') + '\n' +
                                          numbered_code +
                                          '\n```')
        await ctx.message.delete()
        await delete_with_emote(ctx, response_message)


def setup(bot: HelpCenterBot) -> None:
    bot.add_cog(Lines(bot))
    bot.logger.info("Extension [lines] loaded successfully.")
