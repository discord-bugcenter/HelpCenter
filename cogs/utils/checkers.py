from typing import Union

import discord
from discord.ext import commands
from discord.ext.commands import check

from ..utils import custom_errors
from main import HelpCenterBot


def authorized_channels_check(ctx: commands.Context) -> bool:
    if ctx.channel.id in ctx.bot.authorized_channels_id:
        return True

    raise custom_errors.NotAuthorizedChannels(ctx.bot.authorized_channels_id)


def authorized_channels():
    return check(authorized_channels_check)


def is_high_staff_check(bot: HelpCenterBot, user: Union[discord.Member, discord.User]) -> tuple[bool, list[id]]:
    bug_center: discord.Guild = bot.get_guild(bot.bug_center_id)

    member: discord.Member = user
    if isinstance(user, discord.User):
        member = bug_center.get_member(user.id)

    allowed_roles_ids: list[int] = [value for (key, value) in bot.staff_roles.items() if key in ('administrator', 'assistant', 'screening')]

    return discord.utils.find(lambda r: r.id in allowed_roles_ids, member.roles) or member.guild_permissions.administrator, allowed_roles_ids


def is_high_staff():
    async def inner(ctx: commands.Context):
        result, list_ids = is_high_staff_check(ctx.bot, ctx.author)
        if result:
            return True
        raise custom_errors.NotAuthorizedRoles(list_ids)

    return check(inner)
