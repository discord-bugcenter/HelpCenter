import discord
from discord.ext import commands


class Tests(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        print("Extension [tests] chargée avec succès.")

    @commands.command(name="edit_message")
    async def _edit_message(self, ctx, message_id: int, *, new_message_content):
        message = await ctx.channel.fetch_message(message_id)
        try:
            await message.edit(content=new_message_content)
        except:
            await ctx.channel.send("On dirait que je n'ai pas pu modifier ce message !")


def setup(bot):
    bot.add_cog(Tests(bot))
