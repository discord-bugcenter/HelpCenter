from __future__ import annotations

import asyncio
import os
import re
from functools import partial
from typing import TYPE_CHECKING, Literal, cast

import aiohttp
import discord
from discord import SelectOption, app_commands, ui
from discord.ext import commands
from typing_extensions import Self  # TODO: remove on 3.11 release

from utils.api.gist import create_new_gist, delete_gist
from utils.constants import BUG_CENTER_ID
from utils.custom_errors import CustomError

if TYPE_CHECKING:
    from re import Pattern

    from main import HelpCenterBot


GIST_TOKEN = os.environ["GIST_TOKEN"]


class Miscellaneous(commands.Cog):
    def __init__(self, bot: HelpCenterBot) -> None:
        """Miscellaneous will check for files in messages and will convert is as gist, and will also check for discord tokens."""
        self.bot: HelpCenterBot = bot
        self.re_token: Pattern[str] = re.compile(r"[\w\-=]{24}\.[\w\-=]{6}\.[\w\-=]{27}", re.ASCII)

        self.attachement_to_gist_ctx_menu = app_commands.ContextMenu(
            name="Make a gist", callback=self.attachement_to_gist
        )
        self.bot.tree.add_command(self.attachement_to_gist_ctx_menu, guild=discord.Object(id=BUG_CENTER_ID))

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        """Look for discord token on message received."""
        await self.token_revoke(message)

    @commands.Cog.listener()
    async def on_message_edit(self, old_message: discord.Message, new_message: discord.Message) -> None:
        """Look for discord token on message editing."""
        await self.token_revoke(new_message)

    # context_menu command
    async def attachement_to_gist(self, inter: discord.Interaction, message: discord.Message) -> None:
        if not message.attachments:
            raise CustomError("Le message doit contenir un fichier.")

        if len(message.attachments) > 1:

            class SelectFileView(ui.View):
                inter: discord.Interaction
                select: ui.Select[SelectFileView]

                @ui.select(
                    options=[
                        SelectOption(label=attachment.filename, value=str(i))
                        for i, attachment in enumerate(message.attachments)
                    ]
                )
                async def select_file(self, inter: discord.Interaction, select: ui.Select[SelectFileView]) -> None:
                    self.inter = inter
                    self.select = select
                    self.stop()

            view = SelectFileView()
            await inter.response.send_message(
                "Sélectionnez le fichier que vous souhaitez envoyer sur gist.", view=view, ephemeral=True
            )
            await view.wait()
            inter = view.inter

            attachment = message.attachments[int(view.select.values[0])]
        else:
            attachment = message.attachments[0]

        file = await message.attachments[0].read()

        try:
            file_content = file.decode("utf-8")
        except UnicodeDecodeError:
            return

        if txt := (os.path.splitext(attachment.filename)[1] != ".txt"):
            file_name = attachment.filename
        else:

            class SelectExtension(ui.Modal, title="Quel est l'extension du fichier ?"):
                inter: discord.Interaction

                extension: ui.TextInput[Self] = ui.TextInput(
                    label="Extension", placeholder=".txt", min_length=1, max_length=10
                )

                async def on_submit(self, interaction: discord.Interaction) -> None:
                    self.inter = interaction
                    self.stop()

            modal = SelectExtension()
            await inter.response.send_modal(modal)
            await modal.wait()
            inter = modal.inter

            ext = cast(str, modal.extension.value)
            file_name = attachment.filename[: -4 * txt] + ext[ext.startswith(".") :]

        await inter.response.defer(ephemeral=True, thinking=True)
        try:
            json_response = await create_new_gist(GIST_TOKEN, file_name, file_content)
            json_response["html_url"]
        except Exception:
            raise CustomError("Impossible de créer le gist.")

        strategy = (
            inter.edit_original_message
            if inter.response.is_done()
            else partial(inter.response.send_message, ephemeral=True)
        )
        await strategy(content="Un gist a été créé :\n" + f"<{json_response['html_url']}>")

    async def token_revoke(self, message: discord.Message) -> Literal[True] | None:
        tokens_places = [message.clean_content]

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
        headers = {"Authorization": f"Bot {match.group(0)}"}
        url = "https://discord.com/api/v10/users/@me"
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(url=url) as response:
                if response.status == 200:
                    await message.delete()
                    response_dict = await response.json()

                    message_content = f"**{message.author.mention} Vous venez d'envoyer un token de bot valide.**\n"
                    message_content += (
                        f"Celui là a été réinitialisé automatiquement, mais réinitialisez-le aussi vous même sur le "
                        f"**portail dev** (https://discord.com/developers/applications/{response_dict['id']}).\n"
                    )

                    await message.channel.send(message_content, allowed_mentions=discord.AllowedMentions(users=True))

                    gist = await create_new_gist(GIST_TOKEN, "token revoke", match.group(0))
                    await asyncio.sleep(30)
                    await delete_gist(GIST_TOKEN, gist["id"])
                    return True

        # Check if it is eventually a user token.
        url = "https://discord.com/api/v10/users/@me"
        headers = {"Authorization": match.group(0)}
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(url=url) as response:
                if response.status == 200:
                    await message.delete()
                    text = (
                        f"{message.author.mention} vous venez d'envoyer un **token utilisateur**.\n"
                        "**Qu'est-ce que c'est ? ** C'est une sorte de mot de passe qui autorise à contrôler votre compte.\n"
                        "**Changez immédiatement votre mot de passe par précaution**.\n"
                        "Nous vous conseillons aussi d'activer **l'authentification à double facteur (2FA)** si c'est n'est pas encore fait.\n"
                    )
                    await message.channel.send(text, allowed_mentions=discord.AllowedMentions(users=True))
                    return True

        return False

    @commands.Cog.listener()
    async def on_member_update(self, old_member: discord.Member, new_member: discord.Member) -> None:
        if new_member.guild.id != BUG_CENTER_ID:
            return
        if len(new_member.roles) == 1:
            return

        all_separator_roles: list[discord.Role] = [
            role for role in new_member.guild.roles[1:] if role.name == "━━━━━━━━━━━━━━━ㅤ"
        ]

        separator_roles: list[discord.Role] = [
            role for role in all_separator_roles if role.position > new_member.roles[1].position
        ]
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
