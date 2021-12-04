import asyncio
import datetime
import re
from typing import Optional, TYPE_CHECKING

import disnake
from disnake import ui
from disnake.ext import commands

from .utils.custom_errors import COCLinkNotValid, AlreadyProcessingCOC
from .utils.misc import Color
from .utils import codingame
from .utils.codingame import COC, COCMode, COCPlayer, COCPlayerGameStatus
from .utils.i18n import use_current_gettext as _

if TYPE_CHECKING:
    from main import HelpCenterBot, Context
    from utils.types import Person


COC_URL = re.compile(r'https://www\.codingame\.com/clashofcode/clash/(\w{39})')
COC_CODE = re.compile(r'\w{39}')

COC_CHANNEL_ID = 864282088722006036
COC_NOTIFICATION_ROLE_ID = 865173675711135745


class COCDiscord(COC):
    def __init__(self, data: dict, message: disnake.Message = None, author: 'Person' = None) -> None:
        super().__init__(data=data)

        self.message: Optional[disnake.Message] = message
        self.author: Optional['Person'] = author

    @classmethod
    def from_coc(cls, coc: COC, message: disnake.Message = None, author: 'Person' = None) -> 'COCDiscord':
        return cls(coc.data, message, author)


class COCView(ui.View):
    def __init__(self, bot: 'HelpCenterBot', coc_url: str = None) -> None:
        super().__init__(timeout=None)
        self.bot = bot

        coc_url = coc_url or 'https://example.com/'
        self.children.insert(0, ui.Button(label="Join", url=coc_url, row=4))

    @ui.button(label="Subscribe", custom_id="add_coc_notification_role", emoji="🔔")
    async def subscribe(self, _, inter: disnake.MessageInteraction) -> None:
        if not inter.guild or not inter.user:
            return

        member = inter.guild.get_member(inter.user.id) or await inter.guild.fetch_member(inter.user.id)
        role = disnake.utils.get(inter.guild.roles, id=COC_NOTIFICATION_ROLE_ID)
        if role:
            await member.add_roles(role, reason="Subscribe to COC notifications.")

        await inter.response.send_message("Si vous le souhaitez, le bot peut vous retirer le rôle après une certaine durée.", view=RoleSubscription(self.bot), ephemeral=True)

    @ui.button(label="Unsubscribe", custom_id="remove_coc_notification_role", emoji="🔕")
    async def unsubscribe(self, __, inter: disnake.MessageInteraction) -> None:
        if not inter.guild or not inter.user:
            return

        old_task = disnake.utils.find(lambda task: task.get_name() == str(inter.user.id), asyncio.all_tasks(loop=self.bot.loop))

        if old_task:
            old_task.cancel()

        member = inter.guild.get_member(inter.user.id) or await inter.guild.fetch_member(inter.user.id)
        role = disnake.utils.get(inter.guild.roles, id=COC_NOTIFICATION_ROLE_ID)

        if role:
            await member.remove_roles(role, reason="Manually unsubscribe to COC notifications.")


class RoleSubscription(ui.View):
    def __init__(self, bot: 'HelpCenterBot'):
        super().__init__(timeout=None)
        self.bot = bot

    @ui.select(options=[disnake.SelectOption(label=_('30 minutes'), value='1_800'),
                        disnake.SelectOption(label=_('1 heure'), value='3_600'),
                        disnake.SelectOption(label=_('3 heures'), value='10_800'),
                        disnake.SelectOption(label=_('12 heures'), value='43_200'),
                        disnake.SelectOption(label=_('1 journée'), value='86_400')])
    async def give_role(self, select: ui.Select, inter: disnake.MessageInteraction):
        if not inter.user or not inter.guild:
            return
        time = datetime.timedelta(seconds=int(select.values[0]))
        old_task = disnake.utils.find(lambda task: task.get_name() == str(inter.user.id), asyncio.all_tasks(loop=self.bot.loop))

        if old_task:
            old_task.cancel()

        member = inter.guild.get_member(inter.user.id) or await inter.guild.fetch_member(inter.user.id)
        role = disnake.utils.get(inter.guild.roles, id=COC_NOTIFICATION_ROLE_ID)
        if role:
            self.bot.loop.create_task(COCCog.remove_role_after(member, role, time), name=str(inter.user.id))


class COCCog(commands.Cog):
    def __init__(self, bot: 'HelpCenterBot') -> None:
        self.bot = bot

        self.current_coc: list[str] = []

    @commands.Cog.listener()
    async def on_ready(self):
        self.bot.add_view(COCView(self.bot))

    @commands.command('coc',
                      aliases=['clash'],
                      usage='/coc {code/link}',
                      description=_('Publish a clash of code !'))
    async def _coc(self, ctx: 'Context', link: str) -> None:
        """A command to publish a clash of code."""
        if link == 'public':
            cocs = await codingame.fetch_pending_cocs()
            if cocs:
                coc = sorted(cocs, key=lambda coc: len(coc.players))[0]
            else:
                await ctx.send("Aucun COC publique trouvé, réessayez dans quelques instants !", delete_after=10)
                return
        else:
            if match := COC_URL.match(link):
                code = match.group(1)
            elif match := COC_CODE.match(link):
                code = match.group(0)
            else:
                raise COCLinkNotValid(link)

            coc = await self.get_coc(code)

        message = await self.process_coc(coc, ctx.author)

        if ctx.channel.id != COC_CHANNEL_ID:
            await ctx.send(embed=disnake.Embed(title=_("Published !"), url=f"https://discord.com/channels/595218682670481418/{COC_CHANNEL_ID}/{message.id}", colour=Color.green().discord))

    @commands.Cog.listener()
    async def on_message(self, message: disnake.Message) -> None:
        """If a message is equal to a coc url, add a reaction to send it in the coc challenge."""
        if isinstance(message.author, disnake.User):
            return
        if message.channel.id == COC_CHANNEL_ID and not message.author == self.bot.user and (message.author.bot or not message.author.guild_permissions.administrator):
            await message.delete()
        if message.author.bot:
            return

        ctx = await self.bot.get_context(message)
        if ctx.valid:
            return  # a command is already invoked

        if match := COC_URL.match(message.content):
            try:
                coc_message = await self.process_coc(await self.get_coc(match.group(1)), message.author)
            except (COCLinkNotValid, AlreadyProcessingCOC):
                pass
            else:
                if message.channel.id != COC_CHANNEL_ID:
                    await message.channel.send(embed=disnake.Embed(title=_("Published !"), url=f"https://discord.com/channels/595218682670481418/{COC_CHANNEL_ID}/{coc_message.id}", colour=Color.green().discord))

    @staticmethod
    def create_embed(coc_discord: COCDiscord) -> disnake.Embed:
        y_n = (_('no'), _('yes'))
        embed = disnake.Embed(
            title=_("New clash of code !"),
            url="https://www.codingame.com/clashofcode/clash/" + coc_discord.code,
            description=_("> `public` : {0}\n"
                          "> `mode` : {1}\n"
                          "> `started` : {2}\n"
                          "> `finished` : {3}")
                .format(y_n[coc_discord.public],
                        coc_discord.mode.name.lower(),
                        y_n[coc_discord.started],
                        y_n[coc_discord.finished])
        )
        embed.add_field(
            name=_("**Created :**"),
            value=f"<t:{int(coc_discord.creation_time.timestamp())}:R>",
            inline=True
        )
        embed.add_field(
            name=_("**Start planned :**"),
            value=f"<t:{int(coc_discord.start_time.timestamp())}:R>",
            inline=True
        )

        if coc_discord.started and coc_discord.end_time:
            embed.add_field(
                name=_("**End :**"),
                value=f"<t:{int(coc_discord.end_time.timestamp())}:R>",
                inline=True
            )

        def format_player(player: COCPlayer) -> str:
            if coc_discord.started:
                if player.game_status == COCPlayerGameStatus.COMPLETED:
                    string = f"**{player.rank:0>2}. {player.nickname}** - {player.score}% - "
                    if coc_discord.mode == COCMode.SHORTEST:
                        string += f"{player.criterion}chars"
                    else:
                        string += f"{player.human_duration}"
                    return string
                else:  # player.game_status == COCPlayerGameStatus.READY:
                    return f"**NA. {player.nickname}**"
            else:
                return f"**{(player.position or 'NA'): >2}. {player.nickname}**"

        embed.add_field(
            name="**Participants**",
            value="\n".join(format_player(player) for player in coc_discord.players) or _("aucun"),
            inline=False
        )

        if coc_discord.author:
            embed.set_author(
                name=str(coc_discord.author),
                icon_url=coc_discord.author.display_avatar.url
            )

        if coc_discord.reachable:
            if coc_discord.started:
                embed.colour = Color.yellow().discord
            else:
                embed.colour = Color.green().discord
        else:
            embed.colour = Color.red().discord

        return embed

    @staticmethod
    async def remove_role_after(member: disnake.Member, role: disnake.Role, time: datetime.timedelta) -> None:
        await asyncio.sleep(time.total_seconds())
        await member.remove_roles(role, reason=f"Automatic unsubscribe to COC notifications after {time} seconds.")

    async def get_coc(self, code) -> COC:
        try:
            coc = await codingame.fetch_coc(code)
        except codingame.COCCodeNotExist:
            valid = False
        else:
            valid = not (coc.finished is True or (coc.public is True and coc.started is True))

        if not valid:
            raise COCLinkNotValid("https://www.codingame.com/clashofcode/clash/" + code)

        return coc

    async def process_coc(self, coc: COC, author: 'Person') -> disnake.Message:
        if coc.code in self.current_coc:
            raise AlreadyProcessingCOC(coc.code)

        coc_discord = COCDiscord.from_coc(coc, author=author)
        self.current_coc.append(coc.code)

        assert isinstance(tmp := self.bot.get_channel(COC_CHANNEL_ID), discdisnakeord.TextChannel)
        coc_channel: disnake.TextChannel = tmp

        coc_discord.message = await coc_channel.send(content=f"<@&{COC_NOTIFICATION_ROLE_ID}>",
                                                     embed=self.create_embed(coc_discord),
                                                     view=COCView(self.bot, "https://www.codingame.com/clashofcode/clash/" + coc.code),
                                                     allowed_mentions=disnake.AllowedMentions(roles=True))

        self.bot.loop.create_task(self.start_processing(coc_discord))

        return coc_discord.message

    async def start_processing(self, coc_discord: COCDiscord):
        while not coc_discord.finished:
            if not coc_discord.started:
                time = min(15, int(coc_discord.ms_before_start/1000))
            else:
                assert coc_discord.ms_before_end  # Type hinting compliance
                time = min(30, int(coc_discord.ms_before_end/1000))

            await asyncio.sleep(time)

            await coc_discord.update()
            assert coc_discord.message  # Type hinting compliance
            await coc_discord.message.edit(content=None, embed=self.create_embed(coc_discord))
        else:

            self.current_coc.remove(coc_discord.code)


def setup(bot: 'HelpCenterBot') -> None:
    bot.add_cog(COCCog(bot))
    bot.logger.info("Extension [clash_of_code] loaded successfully.")
