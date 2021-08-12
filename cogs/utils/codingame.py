from datetime import timedelta, datetime
from enum import Enum, auto
from typing import Optional
from urllib.parse import urlencode, urlparse, urlunparse
import aiohttp

import pytz


class COC:
    __slots__ = (
        'data',
        'code',
        'nb_players_max',
        'creation_time',
        'start_time',
        'end_time',
        'ms_before_start',
        'ms_before_end',
        'finished',
        'started',
        'public',
        'players',
        'mode'
    )
    
    def __init__(self, *, data: dict) -> None:
        self.data = data
        self._from_data(data)

    @staticmethod
    def parse_date(str_date: Optional[str]) -> Optional[datetime]:
        return datetime.strptime(str_date, '%b %d, %Y %I:%M:%S %p').replace(tzinfo=pytz.UTC) if str_date else None

    def _from_data(self, data: dict) -> None:
        self.code: str = data.get('publicHandle')
        self.nb_players_max: int = data.get('nbPlayersMax')
        self.creation_time: datetime = self.parse_date(data.get('creationTime'))
        self.start_time: datetime = self.parse_date(data.get('startTime'))
        self.end_time: Optional[datetime] = self.parse_date(data.get('endTime'))
        self.ms_before_start: int = data.get('msBeforeStart')
        self.ms_before_end: Optional[int] = data.get('msBeforeEnd')
        self.finished: bool = data.get('finished')
        self.started: bool = data.get('started')
        self.public: bool = data.get('publicClash')
        self.players: list['COCPlayer'] = [COCPlayer(data=playerdata) for playerdata in data.get('players')]
        self.mode: 'COCMode' = COCMode[data.get('mode', 'UNKNOWN')]

    def _update(self, data: dict) -> None:
        self.data.update(data)

        self.start_time = self.parse_date(data.get('startTime'))
        self.end_time = self.parse_date(data.get('endTime'))
        self.ms_before_start = data.get('msBeforeStart')
        self.ms_before_end = data.get('msBeforeEnd')
        self.finished = data.get('finished')
        self.started = data.get('started')
        self.players = [COCPlayer(data=playerdata) for playerdata in data.get('players')]
        self.mode = COCMode[data.get('mode', 'UNKNOWN')]

    @property
    def reachable(self) -> bool:
        return not self.finished and (not self.started or (self.started and not self.public))

    async def update(self):
        async with aiohttp.ClientSession() as session:
            async with session.post('https://www.codingame.com/services/ClashOfCode/findClashReportInfoByHandle', json=[self.code]) as r:
                result = await r.json()

        self._update(data=result)


class COCPlayer:
    __slots__ = (
        'id',
        'nickname',
        'avatar_id',
        'status',
        'game_status',
        'rank',
        'position',
        'score',
        'duration',
        'criterion',
        'language'
    )

    def __init__(self, *, data: dict) -> None:
        self._from_data(data)

    def _from_data(self, data: dict) -> None:
        self.id: int = data.get('codingamerId')
        self.nickname: str = data.get('codingamerNickname')
        self.avatar_id: int = data.get('codingamerAvatarId')
        self.status: 'COCPlayerStatus' = COCPlayerStatus[data.get('status')]
        self.game_status: Optional['COCPlayerGameStatus'] = COCPlayerGameStatus[data.get('testSessionStatus')] if data.get('testSessionStatus') else None
        self.rank: int = data.get('rank')
        self.position: int = data.get('position')
        self.score: Optional[int] = data.get('score')
        self.duration: Optional[timedelta] = timedelta(milliseconds=data['duration']) if data.get('duration') else None
        self.criterion: Optional[int] = data.get('criterion')
        self.language: Optional[str] = data.get('languageId')

    @property
    def avatar_url(self) -> str:
        parsed = urlparse('https://www.codingame.com/servlet/fileservlet')
        parsed = parsed._replace(query=urlencode({'id': self.id, 'format': 'profile_avatar'}))

        return urlunparse(parsed)

    @property
    def human_duration(self) -> Optional[str]:
        if not self.duration: return None
        date = datetime.fromtimestamp(self.duration.total_seconds())
        return date.strftime('%Mm%Ss')



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


# Errors
class COCCodeNotExist(Exception):
    def __init__(self, code: str) -> None:
        """Raised if a COC code does not exist."""
        self.code = code

class NoPendingCOC(Exception):
    pass


async def fetch_coc(code: str) -> COC:
    async with aiohttp.ClientSession() as session:
        async with session.post('https://www.codingame.com/services/ClashOfCode/findClashReportInfoByHandle', json=[code]) as r:
            result = await r.json()

    if result.get('id') == 502:
        raise COCCodeNotExist(code)
    
    return COC(data=result)

async def fetch_pending_cocs() -> Optional[list[COC]]:
    async with aiohttp.ClientSession() as session:
        async with session.post('https://www.codingame.com/services/ClashOfCode/findPendingClashes', json=[]) as r:
            result = await r.json()

    if not result:
        raise NoPendingCOC()
    
    else:
        return [COC(data=data) for data in result]
