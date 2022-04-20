import json

import aiohttp


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
