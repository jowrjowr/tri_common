from .command import Command


class CommandException(Exception):
    pass


class MissingArgument(CommandException):
    pass


class InvalidArgument(CommandException):
    pass
