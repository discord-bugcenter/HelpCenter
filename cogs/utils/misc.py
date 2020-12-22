from schema import Schema, Or, And, Use, Optional

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
