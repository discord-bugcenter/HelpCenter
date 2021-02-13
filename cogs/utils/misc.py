from schema import Schema, Or, And, Use, Optional, Regex
import asyncio
import aiohttp
import json

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
    'description': Or({str: str}, str),
    Optional('author'): int,
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
