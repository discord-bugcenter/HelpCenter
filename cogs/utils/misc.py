from schema import Schema, Or, And, Use, Optional

tag_shema = Schema({
    'name': str,
    'description': str,
    'response': {
        'embed': {
            'title': str,
            'description': Or(str, And(list, Use(lambda iterable: '\n'.join(iterable)))),
            Optional('image'): {
                'url': str
            },
            Optional('fields'): [
                {
                    'name': str,
                    'value': str,
                    Optional('inline'): bool
                }
            ]
        }
    }
})
