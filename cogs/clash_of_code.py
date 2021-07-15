import asyncio
import datetime
import re
from urllib.parse import urlparse, urlencode, urlunparse
from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional

import discord
import aiohttp
import pytz as pytz
from discord.ext import commands

from main import HelpCenterBot
from .utils.custom_errors import COCLinkNotValid, AlreadyProcessingCOC
from .utils.misc import Color
from .utils.i18n import use_current_gettext as _

COC_URL = re.compile(r'https://www\.codingame\.com/clashofcode/clash/(\w{39})')
COC_CODE = re.compile(r'\w{39}')


class COCMode(Enum):
    FASTEST = auto()
    SHORTEST = auto()
    REVERSE = auto()
    UNKNOWN = auto()


class COCPlayerStatus(Enum):
    OWNER = auto()
    STANDARD = auto()


class COCPlayerGameStatus(Enum):
    COMPLETED = auto()
    READY = auto()


@dataclass()
class COCPlayer:
    id: int
    nickname: str
    avatar_id: int
    status: COCPlayerStatus
    game_status: Optional[COCPlayerGameStatus]
    rank: int
    position: int
    score: Optional[int]
    duration: Optional[datetime.timedelta]
    criterion: Optional[int]
    language: Optional[str]

    @property
    def avatar_url(self) -> str:
        parsed = urlparse('https://www.codingame.com/servlet/fileservlet')
        parsed = parsed._replace(query=urlencode({'id': self.id, 'format': 'profile_avatar'}))

        return urlunparse(parsed)

    @property
    def human_duration(self) -> Optional[str]:
        if not self.duration: return None
        date = datetime.datetime.fromtimestamp(self.duration.total_seconds())
        return date.strftime('%Mm%Ss')


@dataclass()
class COCInformations:
    code: str
    message: Optional[discord.Message]
    share_author: Optional[discord.User]
    nb_players_max: int
    creation_time: datetime.datetime
    start_time: datetime.datetime
    end_time: Optional[datetime.datetime]
    ms_before_start: int
    ms_before_end: Optional[int]
    finished: bool
    started: bool
    public: bool
    players: list[COCPlayer]
    mode: COCMode

    @property
    def reachable(self) -> bool:
        return not self.finished and (not self.started or (self.started and not self.public))


class COC(commands.Cog):
    def __init__(self, bot: HelpCenterBot) -> None:
        self.bot = bot

        self.current_coc: list[str] = []
        self.coc_channel_id = 864282088722006036

    @commands.command('coc',
                      aliases=['clash'],
                      usage='/coc {code/link}',
                      description=_('Publish a clash of code !'))
    async def _coc(self, ctx: commands.Context, link: str) -> None:
        """A command to publish a clash of code."""
        if match := COC_URL.match(link):
            code = match.group(1)
        elif match := COC_CODE.match(link):
            code = match.group(0)
        else:
            raise COCLinkNotValid(link)

        message: discord.Message = await self.process_coc(code, ctx.author)
        if ctx.channel.id != self.coc_channel_id:
            await ctx.send(embed=discord.Embed(title=_("Published !"), url=f"https://discord.com/channels/595218682670481418/{self.coc_channel_id}/{message.id}", colour=Color.green().discord))

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        """If a message is equal to a coc url, add a reaction to send it in the coc challenge."""
        if message.channel.id == self.coc_channel_id and not message.author == message.guild.me and not (not message.author.bot and message.author.guild_permissions.administrator):
            await message.delete()
        if message.author.bot: return

        ctx = await self.bot.get_context(message)
        if ctx.valid: return  # a command is already invoked

        if match := COC_URL.match(message.content):
            try: coc_message = await self.process_coc(match.group(1), message.author)
            except (COCLinkNotValid, AlreadyProcessingCOC): pass
            else:
                if message.channel.id != self.coc_channel_id:
                    await message.channel.send(embed=discord.Embed(title=_("Published !"), url=f"https://discord.com/channels/595218682670481418/{self.coc_channel_id}/{coc_message.id}", colour=Color.green().discord))

    @staticmethod
    def parse_player(_json: dict) -> COCPlayer:
        return COCPlayer(
            id=_json.get('codingamerId'),
            nickname=_json.get('codingamerNickname'),
            avatar_id=_json.get('codingamerAvatarId'),
            status=COCPlayerStatus[_json.get('status')],
            game_status=COCPlayerGameStatus[_json.get('testSessionStatus')] if _json.get('testSessionStatus') else None,
            rank=_json.get('rank'),
            position=_json.get('position'),
            score=_json.get('score'),
            duration=datetime.timedelta(milliseconds=_json['duration']) if _json.get('duration') else None,
            criterion=_json.get('criterion'),
            language=_json.get('languageId')
        )

    @staticmethod
    def parse_coc(_json: dict, message: discord.Message = None, author: discord.User = None) -> COCInformations:
        def parse_date(str_date: Optional[str]) -> Optional[datetime.datetime]:
            return datetime.datetime.strptime(str_date, '%b %d, %Y %I:%M:%S %p').replace(tzinfo=pytz.UTC) if str_date else None

        return COCInformations(
            code=_json.get('publicHandle'),
            message=message,
            share_author=author,
            nb_players_max=_json.get('nbPlayersMax'),
            creation_time=parse_date(_json.get('creationTime')),
            start_time=parse_date(_json.get('startTime')),
            end_time=parse_date(_json.get('endTime')),
            ms_before_start=_json.get('msBeforeStart'),
            ms_before_end=_json.get('msBeforeEnd'),
            finished=_json.get('finished'),
            started=_json.get('started'),
            public=_json.get('publicClash'),
            players=[COC.parse_player(player_json) for player_json in _json.get('players')],
            mode=COCMode[_json.get('mode', 'UNKNOWN')]
        )

    @staticmethod
    def create_embed(coc: COCInformations) -> discord.Embed:
        y_n = (_('no'), _('yes'))
        embed = discord.Embed(
            title=_("New clash of code !"),
            url="https://www.codingame.com/clashofcode/clash/" + coc.code,
            description=_("> `public` : {0}\n"
                          "> `mode` : {1}\n"
                          "> `started` : {2}\n"
                          "> `finished` : {3}")
                .format(y_n[coc.public],
                        coc.mode.name.lower(),
                        y_n[coc.started],
                        y_n[coc.finished])
        )
        embed.add_field(
            name=_("**Created :**"),
            value=f"<t:{int(coc.creation_time.timestamp())}:R>",
            inline=True
        )
        embed.add_field(
            name=_("**Start planned :**"),
            value=f"<t:{int(coc.start_time.timestamp())}:R>",
            inline=True
        )

        if coc.started:
            embed.add_field(
                name=_("**End :**"),
                value=f"<t:{int(coc.end_time.timestamp())}:R>",
                inline=True
            )

        def format_player(player: COCPlayer):
            if coc.started:
                if player.game_status == COCPlayerGameStatus.COMPLETED:
                    string = f"**{player.rank:0>2}. {player.nickname}** - {player.score}% - "
                    if coc.mode == COCMode.SHORTEST:
                        string += f"{player.criterion}chars"
                    else:
                        string += f"{player.human_duration}"
                    return string
                if player.game_status == COCPlayerGameStatus.READY:
                    return f"**NA. {player.nickname}**"
            else:
                return f"**{player.position: >2}. {player.nickname}**"

        embed.add_field(
            name="**Participants**",
            value="\n".join(format_player(player) for player in coc.players) or _("aucun"),
            inline=False
        )

        if coc.share_author:
            embed.set_author(
                name=str(coc.share_author),
                icon_url=coc.share_author.avatar.url
            )

        if coc.reachable:
            if coc.started:
                embed.colour = Color.yellow().discord
            else:
                embed.colour = Color.green().discord
        else:
            embed.colour = Color.red().discord

        return embed

    async def process_coc(self, code, author: discord.User) -> discord.Message:
        async with aiohttp.ClientSession() as session:
            async with session.post('https://www.codingame.com/services/ClashOfCode/findClashReportInfoByHandle', json=[code]) as r:
                result = await r.json()

        if result.get('id') == 502 or result.get('finished') is True or (result.get('publicClash') is True and result.get('started') is True):
            raise COCLinkNotValid("https://www.codingame.com/clashofcode/clash/" + code)

        if code in self.current_coc:
            raise AlreadyProcessingCOC(code)

        coc = self.parse_coc(result, author=author)
        self.current_coc.append(code)

        coc_channel: Optional[discord.TextChannel] = self.bot.get_channel(self.coc_channel_id)
        coc.message = await coc_channel.send(embed=self.create_embed(coc))

        self.bot.loop.create_task(self.start_processing(coc))

        return coc.message

    async def start_processing(self, coc: COCInformations):
        while not coc.finished:
            if not coc.started:
                time = min(15, int(coc.ms_before_start/1000))
            else:
                time = min(30, int(coc.ms_before_end/1000))

            await asyncio.sleep(time)

            async with aiohttp.ClientSession() as session:
                async with session.post('https://www.codingame.com/services/ClashOfCode/findClashReportInfoByHandle', json=[coc.code]) as r:
                    result = await r.json()

            coc = self.parse_coc(result, coc.message, coc.share_author)
            await coc.message.edit(embed=self.create_embed(coc))
        else:
            self.current_coc.remove(coc.code)


def setup(bot: HelpCenterBot) -> None:
    bot.add_cog(COC(bot))
    bot.logger.info("Extension [clash_of_code] loaded successfully.")