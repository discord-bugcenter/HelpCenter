import asyncio
import aiohttp
import json

from schema import Schema, Or, And, Use, Optional, Regex
import discord

text_or_list = Schema(Or(str, And(list, Use(lambda iterable: '\n'.join(iterable)))))

embed_shema = Schema({
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

inner_tag_shema = Schema({
    Optional('lang'): Regex(r'[a-z]{2}_[A-Z]{2}'),
    'name': str,
    Optional('aliases'): list,
    'description': str,
    'response': Or({'embed': embed_shema}, {
        'choices': [
            {
                "choice_name": str,
                "embed": embed_shema
            }
        ]
    })
})

tag_shema = Schema(Or([inner_tag_shema], inner_tag_shema))


async def add_reactions(message, reactions) -> None:
    for react in reactions:
        await message.add_reaction(react)


async def delete_with_emote(ctx, bot_message):
    await bot_message.add_reaction("🗑️")

    try:
        await ctx.bot.wait_for("reaction_add", timeout=120,
                               check=lambda react, usr: str(react.emoji) == "🗑️" and react.message.id == bot_message.id and usr.id == ctx.author.id)
    except asyncio.TimeoutError:
        try: await bot_message.remove_reaction("🗑️", ctx.me)
        except: pass
    else:
        try:
            await bot_message.delete()
            await ctx.message.delete()
        except: pass


async def create_new_gist(token, file_name, file_content):
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


async def execute_piston_code(language, version, files: list, *, stdin: list = None, args: list = None):
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
    @classmethod
    def black(cls):
        return cls(0, 0, 0)

    @classmethod
    def grey_embed(cls):
        return cls(47, 49, 54)

    def __init__(self, r, g, b, a=1.0):
        self.r = r
        self.g = g
        self.b = b
        self.a = a

    @property
    def mpl(self):  # matplotlib
        return self.r / 255, self.g / 255, self.b / 255, self.a

    @property
    def discord(self):
        return discord.Color.from_rgb(self.r, self.g, self.b)

    @property
    def rgb(self):
        return self.r, self.g, self.b
