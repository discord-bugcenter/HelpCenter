import discord
from discord.ext.commands import check


def authorized_channels():
    authorized_channels_id = [
        692712497844584448,  # discussion-dev
        595981741542604810,  # aide-dev
        707555362458304663,  # aide-dev-2
        779040873236136007,  # aide-dev-3
        754322079418941441,  # aide-autres
        780123502660681728,  # aide-autres-2
        595224241742413844,  # tests-1
        595224271132033024   # tests-2
    ]
    formated_text = ("Vous ne pouvez pas executer cette commande ici. Essayez dans ces salons :\n"
                     f"<#{'>, <#'.join(str(chan_id) for chan_id in authorized_channels_id)}>")

    async def predicate(ctx):
        if ctx.channel.id in authorized_channels_id:
            return True

        try: await ctx.send(formated_text, delete_after=10)
        except: pass

        return False

    return check(predicate)

