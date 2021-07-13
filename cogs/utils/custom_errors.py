from discord.ext.commands import errors


class NotAuthorizedChannels(errors.CheckFailure):
    def __init__(self, list_channels_id):
        super().__init__()
        self.list_channels_id = list_channels_id

    pass


class NotAuthorizedRoles(errors.CheckFailure):
    def __init__(self, list_roles_id):
        super().__init__()
        self.list_roles_id = list_roles_id

    pass


class NotInBugCenter(errors.CommandError):
    pass


class COCLinkNotValid(errors.BadArgument):
    def __init__(self, link, message=None, *args):
        self.link = link
        super().__init__(message, *args)
    pass


class AlreadyProcessingCOC(errors.BadArgument):
    def __init__(self, code, message=None, *args):
        self.code = code
        super().__init__(message, *args)
    pass
