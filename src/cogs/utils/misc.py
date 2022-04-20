import asyncio
from typing import Union, Iterable, TYPE_CHECKING

from schema import Schema, Or, And, Use, Optional, Regex
import discord

if TYPE_CHECKING:
    from main import HelpCenterBot
    from .types import Person

text_or_list = Schema(Or(str, And(list, Use('\n'.join))))

embed_schema = Schema({
    'title': str,
    'description': text_or_list,
    Optional('image'): {
        'url': str
    },
    Optional('fields'): [
        {
            'name': str,
            'value': text_or_list,
            Optional('inline'): bool
        }
    ]
})

inner_tag_schema = Schema({
    Optional('lang'): Regex(r'[a-z]{2}_[A-Z]{2}'),
    'name': str,
    Optional('aliases'): list,
    'description': str,
    'response': Or({'embed': embed_schema}, {
        'choices': [
            {
                "choice_name": str,
                "embed": embed_schema
            }
        ]
    })
})

tag_schema = Schema(Or([inner_tag_schema], inner_tag_schema))


async def add_reactions(message: discord.Message, reactions: Iterable[Union[discord.Emoji, discord.PartialEmoji, str]]) -> None:
    for react in reactions:
        await message.add_reaction(react)


async def delete_with_emote(bot: 'HelpCenterBot', author: 'Person', message: discord.Message) -> None:
    assert bot.user is not None, "Bot must be logged out to use this function."

    await message.add_reaction("🗑️")

    try:
        await bot.wait_for("reaction_add", timeout=120,
                           check=lambda react, usr: str(react.emoji) == "🗑️" and react.message.id == message.id and usr.id == author.id)
    except asyncio.TimeoutError:
        try:
            await message.remove_reaction("🗑️", bot.user)
        except discord.HTTPException:
            pass
        return
    try:
        await message.delete()
    except discord.HTTPException:
        pass


class Color:
    def __init__(self, r: int, g: int, b: int, a: int = 1) -> None:
        """Represent a Color object with pre-done colors that can be used as discord.Color etc..."""
        self.r = r
        self.g = g
        self.b = b
        self.a = a

    @classmethod
    def black(cls):
        return cls(0, 0, 0)

    @classmethod
    def grey_embed(cls):
        return cls(47, 49, 54)

    @classmethod
    def green(cls):
        return cls(87, 242, 135)

    @classmethod
    def red(cls):
        return cls(237, 66, 69)

    @classmethod
    def yellow(cls):
        return cls(254, 231, 92)

    @property
    def mpl(self):  # matplotlib
        return self.r / 255, self.g / 255, self.b / 255, self.a

    @property
    def discord(self):
        return discord.Color.from_rgb(self.r, self.g, self.b)

    @property
    def rgb(self):
        return self.r, self.g, self.b
