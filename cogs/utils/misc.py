from schema import Schema, Or, And, Use, Optional
import asyncio
import aiohttp
import json

embed_shema = Schema({
    'title': str,
    'description': Or(str, And(list, Use(lambda iterable: '\n'.join(iterable)))),
    Optional('image'): {
        'url': str
    },
    Optional('fields'): [
        {
            'name': str,
            'value': Or(str, And(list, Use(lambda iterable: '\n'.join(iterable)))),
            Optional('inline'): bool
        }
    ]
})

tag_shema = Schema({
    'name': str,
    Optional('aliases'): list,
    'description': str,
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
