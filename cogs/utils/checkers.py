import discord
from discord.ext import commands
from discord.ext.commands import check

from ..utils import custom_errors


def authorized_channels_check(ctx: commands.Context) -> bool:
    if ctx.channel.id in ctx.bot.authorized_channels_id:
        return True

    raise custom_errors.NotAuthorizedChannels(ctx.bot.authorized_channels_id)


def authorized_channels():
    return check(authorized_channels_check)


def is_high_staff():
    async def inner(ctx: commands.Context):
        member: discord.Member = auth if isinstance(auth := ctx.author, discord.Member) else ctx.bot.get_guild(ctx.bot.bug_center_id).get_member(ctx.author.id)
        allowed_roles_ids = [value for key, value in ctx.bot.staff_roles.items() if key in ['administrator', 'assistant', 'screening', 'brillant']]
        if discord.utils.find(lambda r: r.id in allowed_roles_ids, member.roles) or member.permissions_in(ctx.channel).administrator:
            return True
        raise custom_errors.NotAuthorizedRoles(allowed_roles_ids)

    return check(inner)
