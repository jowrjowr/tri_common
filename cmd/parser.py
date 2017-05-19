from argparse import Action as _Action


class Option(_Action):
    """
    Action classed used for the commands.

    Stores all the specified options with optional arguments as a dictionary in the given namespace as
    a JSON formatted string.
    """
    def __call__(self, _, namespace, values, option_string=None):
        from json import dumps, loads

        commands = loads(getattr(namespace, 'pkg_options', '{}'))

        option = option_string[2:]

        if option in commands:
            raise NotImplementedError("You cannot choose an option twice ({0}).".format(option_string))

        if values is None or len(values) == 0:
            commands[option] = None
        elif type(values) == str:
            commands[option] = values
        else:
            commands[option] = values[0]

        setattr(namespace, 'pkg_options', dumps(commands))


def init_parser():
    """
    Initializes the command parser.

    Command options are dynamically loaded from packages within the commands package.

    :returns ArgumentParser: argument parser object
    """
    import commands as commands
    from argparse import ArgumentParser
    from importlib import import_module
    from inspect import getmembers, isclass
    from pkgutil import iter_modules

    arg_parser = ArgumentParser()

    # options
    opt_parser = arg_parser.add_argument_group("options")
    log_opt_parser = opt_parser.add_mutually_exclusive_group()
    log_opt_parser.add_argument("-d", "--debug", action="store_true", help="enable debug logging")
    log_opt_parser.add_argument("-q", "--quiet", action="store_true", help="disable debug/info logging")

    # commands
    cmd_parser = arg_parser.add_subparsers(title="commands")

    for _, pkg_name, is_pkg in iter_modules(commands.__path__):
        if is_pkg:
            pkg_module = import_module("cmd.{0}".format(pkg_name))

            pkg_parser = cmd_parser.add_parser(pkg_name)
            pkg_parser.set_defaults(pkg_module=pkg_module, pkg_parser=pkg_parser)

            # use this to store groups and add commands to them as needed
            opt_groups = {}

            for opt_name, opt_class in getmembers(pkg_module, isclass):
                if opt_class.group is None:
                    opt_parser = pkg_parser
                else:
                    opt_parser = opt_groups.get(opt_class.group, pkg_parser.add_argument_group(opt_class.group))

                    opt_groups[opt_class.group] = opt_parser

                if opt_class.arg is None:
                    opt_parser.add_argument(opt_class.option(),
                                            nargs=0, help=opt_class.help,
                                            const=None, action=Option)
                elif opt_class.arg[0] == "?":
                    opt_parser.add_argument(opt_class.option(),
                                            nargs="?", help=opt_class.help,
                                            const=None, metavar=opt_class.arg[1:],
                                            action=Option)
                else:
                    opt_parser.add_argument(opt_class.option(),
                                            nargs=1, help=opt_class.help,
                                            const=None, metavar=opt_class.arg,
                                            action=Option)

    return arg_parser
