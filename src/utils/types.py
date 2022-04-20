from typing import Union

from discord import User, Member
from discord.ext.commands import Context as Ctx

from src.main import HelpCenterBot

Person = Union[User, Member]
Snowflake = int
Context = Ctx[HelpCenterBot]
