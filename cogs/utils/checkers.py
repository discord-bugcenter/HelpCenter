from typing import Union

import discord
from discord.ext import commands
from discord.ext.commands import check

from . import custom_errors
from .constants import BUG_CENTER_ID, STAFF_ROLES
from main import HelpCenterBot


def authorized_channels_check(ctx: commands.Context) -> bool:
    target = ctx.channel.id
    if isinstance(ctx.channel, discord.Thread):
        target = ctx.channel.parent_id

    if target in ctx.bot.authorized_channels_id:
        return True

    raise custom_errors.NotAuthorizedChannels(ctx.bot.authorized_channels_id)


def authorized_channels():
    return check(authorized_channels_check)


def is_high_staff_check(bot: HelpCenterBot, user: Union[discord.Member, discord.User]) -> tuple[bool, list[int]]:
    assert (tmp := bot.get_guild(BUG_CENTER_ID))
    bug_center: discord.Guild = tmp

    if isinstance(user, discord.User):
        assert (tmp := bug_center.get_member(user.id))
        member: discord.Member = tmp
    else:
        member = user

    allowed_roles_ids: list[int] = [value for (key, value) in STAFF_ROLES.items() if key in ('administrator', 'assistant', 'screening')]

    return bool(discord.utils.find(lambda r: r.id in allowed_roles_ids, member.roles)) or member.guild_permissions.administrator, allowed_roles_ids


def is_high_staff():
    async def inner(ctx: commands.Context):
        result, list_ids = is_high_staff_check(ctx.bot, ctx.author)
        if result:
            return True
        raise custom_errors.NotAuthorizedRoles(list_ids)

    return check(inner)
