from discord.app_commands import errors


class CustomError(errors.AppCommandError):
    """
    The base error used for non-specific errors.
    """

    pass
