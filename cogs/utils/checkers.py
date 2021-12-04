from typing import Union

import disnake
from disnake.ext import commands
from disnake.ext.commands import check

from . import custom_errors
from .constants import BUG_CENTER_ID, STAFF_ROLES, AUTHORIZED_CHANNELS_IDS
from main import HelpCenterBot


def authorized_channels_check(ctx: Union[disnake.ApplicationCommandInteraction, commands.Context]) -> bool:
    target = ctx.channel.id
    if isinstance(ctx.channel, disnake.Thread):
        target = ctx.channel.parent_id

    if target in AUTHORIZED_CHANNELS_IDS:
        return True

    raise custom_errors.NotAuthorizedChannels(AUTHORIZED_CHANNELS_IDS)


def authorized_channels():
    return check(authorized_channels_check)


def is_high_staff_check(bot: HelpCenterBot, user: Union[disnake.Member, disnake.User]) -> tuple[bool, list[int]]:
    assert (tmp := bot.get_guild(BUG_CENTER_ID))
    bug_center: disnake.Guild = tmp

    if isinstance(user, disnake.User):
        assert (tmp := bug_center.get_member(user.id))
        member: disnake.Member = tmp
    else:
        member = user

    allowed_roles_ids: list[int] = [value for (key, value) in STAFF_ROLES.items() if key in ('administrator', 'assistant', 'screening')]

    return bool(disnake.utils.find(lambda r: r.id in allowed_roles_ids, member.roles)) or member.guild_permissions.administrator, allowed_roles_ids


def is_high_staff():
    async def inner(ctx: Union[disnake.ApplicationCommandInteraction, commands.Context]):
        result, list_ids = is_high_staff_check(ctx.bot, ctx.author)  # type: ignore
        if result:
            return True
        raise custom_errors.NotAuthorizedRoles(list_ids)

    return check(inner)
