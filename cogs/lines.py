from typing import TYPE_CHECKING, Optional

import disnake
from disnake.ext import commands

from .utils.misc import delete_with_emote
from .utils import checkers
from .utils.i18n import use_current_gettext as _

if TYPE_CHECKING:
    from main import HelpCenterBot


LANGUAGES = ["python", "javascript", "typescript", "java", "rust", "lisp", "elixir"]


async def lines_autocomplete(inter: disnake.ApplicationCommandInteraction, user_input: str) -> list[str]:
    return [lang for lang in LANGUAGES + [user_input] if user_input.lower() in lang]


class Lines(commands.Cog):
    def __init__(self, bot: 'HelpCenterBot') -> None:
        self.bot = bot

    @commands.slash_command(
        name='lines',
        desc=_('Add the lines number to your code.')
    )
    @checkers.authorized_channels()
    async def lines(self,
                    ctx: disnake.ApplicationCommandInteraction,
                    code: str = commands.Param(description=_('The code to add the lines number to.')),
                    language: Optional[str] = commands.Param(None, autocomplete=lines_autocomplete, description=_('The language your code is in.'))) -> None:
        """A command that add number before each lines."""
        numbered_code = '\n'.join(f'{i+1:>3} | {line}' for i, line in enumerate(code.splitlines()))
        if len(numbered_code) > 1950:
            numbered_code = numbered_code[:1950] + '\netc...'

        await ctx.send(_('Numbered code of {ctx.author} :\n').format(**locals()) +
                       '```' + (language or '') + '\n' +
                       numbered_code +
                       '\n```')
        await delete_with_emote(self.bot, ctx.author, await ctx.original_message())


def setup(bot: 'HelpCenterBot') -> None:
    bot.add_cog(Lines(bot))
    bot.logger.info("Extension [lines] loaded successfully.")
