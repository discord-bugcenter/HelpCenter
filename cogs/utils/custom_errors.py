from discord.ext.commands import errors


class NotAuthorizedChannels(errors.CheckFailure):
    def __init__(self, list_channels_id: list[int]) -> None:
        """Raised if a command is executed in a unauthorized channel."""
        self.list_channels_id = list_channels_id
        super().__init__()


class NotAuthorizedRoles(errors.CheckFailure):
    def __init__(self, list_roles_id: list[int]) -> None:
        """Raised if a command is executed while a member is unauthorized."""
        self.list_roles_id = list_roles_id
        super().__init__()


class NotInBugCenter(errors.CommandError):
    pass


class COCLinkNotValid(errors.BadArgument):
    def __init__(self, link: str, message: str = None, *args) -> None:
        """Raised if a COC link is not valide."""
        self.link = link
        super().__init__(message, *args)


class AlreadyProcessingCOC(errors.BadArgument):
    def __init__(self, code: str, message: str = None, *args) -> None:
        """Raised if a COC is already processing."""
        self.code = code
        super().__init__(message, *args)
