import discord
from discord.ext.commands import Context
from discord_slash import SlashContext


def authorized_channels(func):
    authorized_channels_id = [624312250806566932]
    formated_text = ("Vous ne pouvez pas executer cette commande ici. Essayez dans ces salons :\n"
                     f"<#{'>, <#'.join(str(chann_id) for chann_id in authorized_channels_id)}>")

    async def wrapper(*args, **kwargs):
        ctx = discord.utils.find(lambda arg: isinstance(arg, Context) or isinstance(arg, SlashContext), args)
        if ctx.channel.id in authorized_channels_id:
            return await func(*args, **kwargs)

        if isinstance(ctx, Context):
            try: await ctx.send(formated_text, delete_after=10)
            except: pass
            finally: return func

        if isinstance(ctx, SlashContext):
            try: await ctx.send(content=formated_text, complete_hidden=True)
            except: pass
            finally: return func

    return wrapper

