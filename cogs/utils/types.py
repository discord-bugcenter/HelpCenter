from typing import Union

from disnake import User, Member
from disnake.ext.commands import Context as Ctx

from main import HelpCenterBot

Person = Union[User, Member]
Snowflake = int
Context = Ctx[HelpCenterBot]
