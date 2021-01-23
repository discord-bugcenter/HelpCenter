"""
1: Transform file attachments (like message.txt, main.js, etc...) to a gist.
2: if the bot detect a token, it will create a gist to revoke it.
"""

import asyncio
import os
import re

import aiohttp
import discord
from discord.ext import commands
import filetype

from .utils.misc import create_new_gist, add_reactions


class Miscellaneous(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.re_token = re.compile(r"[\w\-=]+\.[\w\-=]+\.[\w\-=]+", re.ASCII)
        print("Extension [miscellaneous] chargée avec succès.")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if await self.token_revoke(message): return
        if message.channel.id not in self.bot.authorized_channels_id: return
        await self.attachement_to_gist(message)

    async def attachement_to_gist(self, message):
        if not message.attachments: return
        else: attachment = message.attachments[0]

        file = await message.attachments[0].read()
        if filetype.guess(file) is not None: return

        try: file_content = file.decode('utf-8')
        except: return await message.channel.send('Une erreur est survenue', delete_after=5)

        if await self.token_revoke(message, attach_content=file_content): return

        await message.add_reaction('🔄')
        try: _, user = await self.bot.wait_for('reaction_add', check=lambda react, usr: not usr.bot and react.message.id == message.id and str(react.emoji) == '🔄', timeout=120)
        except asyncio.TimeoutError: return
        finally: await message.clear_reactions()

        references = {
            '<:javascript:664540815086845952>': 'js',
            '<:python:664539154838978600>': 'py',
            '<:html:706981296710352997>': 'html',
            '<:php:664540814944370689>': 'php',
            '<:java:664540814772273163>':  'java',
            '<:go:665975979402985483>': 'go',
            '<:lua:664539154788515902>': 'lua',
            '<:ruby:664540815078588436>': 'rb',
            '<:rust:664539155329581094>': 'rs',
            '<:scala:665967129660751883>': 'scala',
            '<:swift:664540815821111306>': 'swift'
        }

        response_message = None
        if os.path.splitext(attachment.filename)[1] in tuple(f'.{ext}' for ext in references.values()):
            file_name = attachment.filename
        else:
            response_message = await message.reply(("Quel est le langage de programmation ?\n"
                                                    "Cliquez sur la réaction correspondante, ou envoyez un message avec l'extension (`.js`, `.py`...)\n\n"
                                                    f"{' '.join(references.keys())}"), mention_author=False)

            task = self.bot.loop.create_task(add_reactions(response_message, references.keys()))

            done, pending = await asyncio.wait([
                self.bot.wait_for('message', timeout=120, check=lambda msg: msg.author.id == user.id and msg.channel.id == response_message.channel.id and len(msg.content) < 7 and msg.content.startswith('.')),
                self.bot.wait_for('reaction_add', timeout=120, check=lambda react, usr: usr.id == user.id and str(react.emoji) in references.keys())
            ], return_when=asyncio.FIRST_COMPLETED)

            try:
                stuff = done.pop().result()
                if isinstance(stuff, tuple):  # A reaction has been added
                    file_name = f"code.{references.get(str(stuff[0].emoji))}"
                else:
                    file_name = f"code{stuff.content}"
            except asyncio.TimeoutError: return
            finally:
                task.cancel()
                await response_message.clear_reactions()
                for future in done:
                    future.exception()
                for future in pending:
                    future.cancel()
        async with message.channel.typing():
            try:
                json_response = await create_new_gist(os.getenv('GIST_TOKEN'), file_name, file_content)
                assert json_response.get('html_url')
            except: return await message.channel.send('Une erreur est survenue', delete_after=5)

        if not response_message:
            await message.reply(content=f"Un gist a été créé :\n<{json_response['html_url']}>", mention_author=False)
        else:
            await response_message.edit(content=f"Un gist a été créé :\n<{json_response['html_url']}>")

    async def token_revoke(self, message, attach_content=None):
        if attach_content:
            match = self.re_token.search(attach_content)
        else:
            match = self.re_token.search(message.content)
        if not match: return

        headers = {
            "Authorization": f"Bot {match.group(0)}"
        }
        url = "https://discord.com/api/v8/users/@me"
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(url=url) as response:
                if response.status == 200:
                    await message.delete()
                    await message.channel.send((f"**{message.author.mention} vous venez d'envoyer un token de bot valide.**\n"
                                                "Celui-ci va être révoqué, mais faites tout de même attention et vérifiez qu'il ai bien été réinitialisé sur le **portail dev**.\n"
                                                "https://discord.com/developers/applications"), allowed_mentions=discord.AllowedMentions.all())

                    await create_new_gist(os.getenv('GIST_TOKEN'), 'token revoke', match.group(0))
                    return True


def setup(bot):
    bot.add_cog(Miscellaneous(bot))
