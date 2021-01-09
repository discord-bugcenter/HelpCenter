from discord.ext.commands import check

import custom_errors


def authorized_channels_check(ctx):
    if ctx.channel.id in ctx.bot.authorized_channels_id:
        return True

    raise custom_errors.NotAuthorizedChannels(ctx.channel)


def authorized_channels():
    return check(authorized_channels_check)

