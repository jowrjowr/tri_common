#!/usr/bin/python3


def run():
    from cmd import init_parser
    from json import loads

    arg_parser = init_parser()
    args = arg_parser.parse_args()

    try:
        pkg_module = getattr(args, "pkg_module")
    except AttributeError:
        arg_parser.print_help()
        return

    try:
        pkg_options = loads(getattr(args, "pkg_options"))
    except AttributeError:
        getattr(args, "pkg_parser").print_help()
        return

    kwargs = {}

    for pkg_option in pkg_options:
        command = getattr(pkg_module, pkg_option.title().replace("-", ""))

        kwargs['argument'] = pkg_options[pkg_option]
        kwargs = command.execute(**kwargs)


run()
