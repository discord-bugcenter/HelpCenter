from schema import Schema, Or, And, Use, Optional
import asyncio

embed_shema = Schema({
    'embed': {
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
    }
})

tag_shema = Schema({
    'name': str,
    'description': str,
    'response': Or(embed_shema, {
        'choice': {
            str: embed_shema
        }
    })
})


async def add_reactions(message, reactions) -> None:
    for react in reactions:
        await message.add_reaction(react)


async def delete_with_emote(ctx, bot_message):
    await bot_message.add_reaction("🗑️")

    try:
        await ctx.bot.wait_for("reaction_add", timeout=120,
                               check=lambda react, usr: str(react.emoji) == "🗑️" and react.message.channel.id == ctx.channel.id and usr.id == ctx.author.id)
    except asyncio.TimeoutError:
        try: await bot_message.remove_reaction("🗑️", ctx.me)
        except: pass
    else:
        await bot_message.delete()
        await ctx.message.delete()
