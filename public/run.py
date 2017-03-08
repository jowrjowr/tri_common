#!/usr/bin/python3

import argparse as _argparse
import commands as _commands
import common.logger as _logger
import importlib as _importlib
import inspect as _inspect
import json as _json
import pkgutil as _pkgutil
import re as _re


def main():
    parser = _argparse.ArgumentParser()

    # logging options
    options_parser = parser.add_argument_group("options")
    options_parser.add_argument("--debug", action="store_true", default=False)
    options_parser.add_argument("--log-single", action="store_true", default=False)
    options_parser.add_argument("--log-verbose", action="store_true", default=False)

    # command parser
    commands_parser = parser.add_subparsers(title="commands")
    for _, modname, is_pkg in _pkgutil.iter_modules(_commands.__path__):
        if is_pkg:
            module = _importlib.import_module("commands." + modname)

            command_parser = commands_parser.add_parser(modname)
            command_parser.set_defaults(command=module)

            for name, command in _inspect.getmembers(module, _inspect.isclass):
                option = "--{0}".format(_re.sub(r"(\w)([A-Z])", r"\1-\2", command.__name__).lower())

                if command.__metavar__ is None:
                    command_parser.add_argument(option, help=command.__description__,
                                                nargs=0, action=CommandAction, const=None)
                elif command.__metavar_require__:
                    command_parser.add_argument(option, help=command.__description__, metavar=command.__metavar__,
                                                nargs=1, action=CommandAction)
                else:
                    command_parser.add_argument(option,  help=command.__description__, metavar=command.__metavar__,
                                                nargs='?', action=CommandAction, const=None)

    arguments = parser.parse_args()

    # initialize logging
    log_lvl = _logger.LogLevel.INFO
    log_mod = _logger.LogMode.DAILY
    log_fmt = _logger.LogFormat.TIMESTAMP

    if arguments.debug:
        log_lvl = _logger.LogLevel.DEBUG

    if arguments.log_single:
        log_mod = _logger.LogMode.SINGLE

    if arguments.log_verbose:
        log_fmt = _logger.LogFormat.TIMESTAMP

    _logger.init(log_lvl=log_lvl, log_mod=log_mod, log_fmt=log_fmt)

    # get command module
    try:
        module = getattr(arguments, "command")
    except AttributeError:
        parser.print_help()
        return

    # get commands & arguments
    try:
        arguments = _json.loads(getattr(arguments, "commands"))
    except AttributeError:
        parser.print_help()
        return

    # execute commands
    kwargs = {}
    for key in arguments:
        option_name = key.title().replace("-", "")

        try:
            option = getattr(module, option_name)
        except AttributeError:
            raise AttributeError("Command {0} in {1} could no be found.".format(option_name, module))

        kwargs = option()(arguments[key], **kwargs)


class CommandAction(_argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        commands = _json.loads(getattr(namespace, 'commands', '{}'))

        if option_string[2:] in commands:
            raise Exception("You cannot choose an option twice ({0}).".format(option_string))

        if values is None or len(values) == 0:
            commands[option_string[2:]] = None
        elif type(values) == str:
            commands[option_string[2:]] = values
        else:
            commands[option_string[2:]] = values[0]

        setattr(namespace, 'commands', _json.dumps(commands))

if __name__ == '__main__':
    main()
