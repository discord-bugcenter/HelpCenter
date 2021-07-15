import asyncio
from typing import Union

import aiohttp
import json

from discord.ext import commands
from schema import Schema, Or, And, Use, Optional, Regex
import discord

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


async def add_reactions(message: discord.Message, reactions: list[Union[discord.Emoji, discord.PartialEmoji, str]]) -> None:
    for react in reactions:
        await message.add_reaction(react)


async def delete_with_emote(ctx: commands.Context, bot_message: discord.Message) -> None:
    await bot_message.add_reaction("🗑️")

    try:
        await ctx.bot.wait_for("reaction_add", timeout=120,
                               check=lambda react, usr: str(react.emoji) == "🗑️" and react.message.id == bot_message.id and usr.id == ctx.author.id)
    except asyncio.TimeoutError:
        try: await bot_message.remove_reaction("🗑️", ctx.me)
        except discord.HTTPException: pass
    else:
        try:
            await bot_message.delete()
            await ctx.message.delete()
        except discord.HTTPException: pass


async def create_new_gist(token: str, file_name: str, file_content: str) -> dict:
    url = 'https://api.github.com/gists'
    header = {
        'Authorization': f'token {token}'
    }
    payload = {
        'files': {file_name: {'content': file_content}},
        'public': True
    }
    async with aiohttp.ClientSession(headers=header) as session:
        async with session.post(url=url, json=payload) as response:
            return json.loads(await response.text())


async def delete_gist(token: str, gist_id: str) -> bool:
    url = 'https://api.github.com/gists/' + gist_id
    header = {
        'Authorization': f'token {token}'
    }
    async with aiohttp.ClientSession(headers=header) as session:
        async with session.delete(url=url):
            return True


async def execute_piston_code(language: str, version: str, files: list, *, stdin: list = None, args: list = None) -> dict:
    url = "https://emkc.org/api/v2/piston/execute"
    payload = {
        'language': language,
        'version': version,
        'files': files
    }
    if stdin:
        payload['stdin'] = stdin
    if args:
        payload['args'] = args

    async with aiohttp.ClientSession() as session:
        async with session.post(url=url, json=payload) as response:
            json_response: dict = await response.json()
            if response.status == 200:
                return json_response['run']
            raise Exception(json_response.get('message', 'unknown error'))


class Color:
    def __init__(self, r: int, g: int, b: int, a: int = 1.0) -> None:
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
