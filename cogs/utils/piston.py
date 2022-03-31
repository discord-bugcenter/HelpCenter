from typing import Optional

import aiohttp


async def execute_piston_code(language: str, version: str, files: list, *, stdin: Optional[list] = None, args: Optional[list] = None) -> dict:
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
