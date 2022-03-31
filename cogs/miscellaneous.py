import asyncio
import os
import re

import aiohttp
import discord
import filetype
from discord.ext import commands

from main import HelpCenterBot
from .utils.misc import add_reactions
from .utils.gist import create_new_gist, delete_gist
from .utils.i18n import _
from .utils.constants import BUG_CENTER_ID, AUTHORIZED_CHANNELS_IDS


GIST_TOKEN = os.environ['GIST_TOKEN']


class Miscellaneous(commands.Cog):
    def __init__(self, bot: HelpCenterBot) -> None:
        """Miscellaneous will check for files in messages and will convert is as gist, and will also check for discord tokens."""
        self.bot = bot
        self.re_token = re.compile(r"[\w\-=]{24}\.[\w\-=]{6}\.[\w\-=]{27}", re.ASCII)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if await self.token_revoke(message):
            return

        if message.channel.id not in AUTHORIZED_CHANNELS_IDS:
            return

        await self.attachement_to_gist(message)

    @commands.Cog.listener()
    async def on_message_edit(self, old_message: discord.Message, new_message: discord.Message) -> None:
        """Look for discord token on message editing."""

        await self.token_revoke(new_message)

    async def attachement_to_gist(self, message: discord.Message) -> None:
        if not message.attachments:
            return
        else:
            attachment = message.attachments[0]

        file = await message.attachments[0].read()
        if filetype.guess(file) is not None:
            return

        try:
            file_content = file.decode('utf-8')
        except UnicodeDecodeError:
            return

        if await self.search_for_token(message, file_content):
            return

        await message.add_reaction('🔄')
        try:
            __, user = await self.bot.wait_for('reaction_add', check=lambda react, usr: not usr.bot and react.message.id == message.id and str(react.emoji) == '🔄', timeout=600)
        except asyncio.TimeoutError:
            return
        finally:
            await message.clear_reactions()

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
            response_message = await message.reply((_("What's the programmation language ?\n", message.author) +
                                                    _("Click on the correspondant reaction, or send a message with the extension (`.js`, `.py`...)\n\n", message.author) +
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
            except asyncio.TimeoutError:
                return
            finally:
                task.cancel()
                await response_message.clear_reactions()
                for future in done:
                    future.exception()
                for future in pending:
                    future.cancel()
        async with message.channel.typing():
            try:
                json_response = await create_new_gist(GIST_TOKEN, file_name, file_content)
                assert json_response.get('html_url')
            except Exception:
                await message.channel.send(_('An error occurred.', message.author), delete_after=5)
                return

        if not response_message:
            await message.reply(content=_("A gist has been created :\n", message.author) + f"<{json_response['html_url']}>", mention_author=False)
        else:
            await response_message.edit(content=_("A gist has been created :\n", message.author) + f"<{json_response['html_url']}>")

    async def token_revoke(self, message):
        tokens_places = [
            message.clean_content
        ]

        for embed in message.embeds:
            tokens_places.append(str(embed.author))
            tokens_places.append(str(embed.description))
            tokens_places.append(str(embed.footer))
            tokens_places.append(str(embed.title))
            tokens_places.append(str(embed.url))
            tokens_places.append(str(embed.image.url))
            for field in embed.fields:
                tokens_places.append(str(field.name))
                tokens_places.append(str(field.value))

        for place in tokens_places:
            if await self.search_for_token(message, place):
                return True

    async def search_for_token(self, message: discord.Message, text: str) -> bool:
        if not (match := self.re_token.search(text)):
            return False
        headers = {
            "Authorization": f"Bot {match.group(0)}"
        }
        url = "https://discord.com/api/v9/users/@me"
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(url=url) as response:
                if response.status == 200:
                    await message.delete()
                    response_dict = await response.json()

                    message_content = _("**{message.author.mention} you just sent a valid bot token.**\n", message.author).format(message=message)
                    message_content += _("This one will be revoked, but be careful and check that it has been successfully reset on the "
                                         "**dev portal** (https://discord.com/developers/applications/{}).\n", message.author).format(response_dict['id'])

                    await message.channel.send(message_content, allowed_mentions=discord.AllowedMentions(users=True))

                    gist = await create_new_gist(GIST_TOKEN, 'token revoke', match.group(0))
                    await asyncio.sleep(30)
                    await delete_gist(GIST_TOKEN, gist['id'])
                    return True

        # Check if it is eventually a user token.
        url = "https://discord.com/api/v9/users/@me"
        headers = {
            "Authorization": match.group(0)
        }
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(url=url) as response:
                if response.status == 200:
                    await message.delete()
                    text = _(f"{message.author.mention} you just sent a valid **user token**.\n"
                             "**What is it? ** This is a kind of password that allows access to a contentious account without a username, password or IP address verification.\n"
                             "**Change your password as a precaution**.\n"
                             "We also recommend that you enable**two-factor authentication, or 2FA.** (settings)\n", message.author)
                    await message.channel.send(text, allowed_mentions=discord.AllowedMentions(users=True))
                    return True

        return False

    @commands.Cog.listener()
    async def on_member_update(self, old_member: discord.Member, new_member: discord.Member):
        if new_member.guild.id != BUG_CENTER_ID:
            return
        if len(new_member.roles) == 1:
            return

        all_separator_roles: list[discord.Role] = [role for role in new_member.guild.roles[1:] if role.name == '━━━━━━━━━━━━━━━ㅤ']

        separator_roles: list[discord.Role] = [role for role in all_separator_roles if role.position > new_member.roles[1].position]
        needed_separators: list[discord.Role] = []

        member_roles: list[discord.Role] = [role for role in new_member.roles[1:] if role not in separator_roles]

        for member_role in member_roles:
            if not separator_roles:
                break

            if member_role.position > separator_roles[0].position:
                needed_separators.append(separator_roles[0])
                separator_roles = [role for role in separator_roles if role.position > member_role.position]

        roles_to_add: set[discord.Role] = set(needed_separators) - set(new_member.roles)
        roles_to_remove: set[discord.Role] = set(all_separator_roles) & set(new_member.roles) - set(needed_separators)

        if roles_to_add:
            await new_member.add_roles(*roles_to_add)
        if roles_to_remove:
            await new_member.remove_roles(*roles_to_remove)


async def setup(bot: HelpCenterBot) -> None:
    await bot.add_cog(Miscellaneous(bot))
    bot.logger.info("Extension [miscellaneous] loaded successfully.")
