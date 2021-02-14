from discord.ext.commands import errors


class NotAuthorizedChannels(errors.CheckFailure):
    def __init__(self, channel, list_channels_id):
        super().__init__()
        self.channel = channel
        self.list_channels_id = list_channels_id

    pass
