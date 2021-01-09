from discord.ext.commands import errors


class NotAuthorizedChannels(errors.CheckFailure):
    def __init__(self, channel):
        super().__init__()
        self.channel = channel

    pass
