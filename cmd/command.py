class Command:
    """
    Abstract class used for any CLI commands. In order to implemented a custom command simply inherit this class
    and implement the execute method and the class variables if required.

    :cvar help: text displayed in the command line

    :cvar group: group under which the command is displayed

    :cvar arg: argument displayed in the command line and also used to determine
    whether the command requires an argument or not. none for no argument, "?" prefix for optional and anything else
    for mandatory.
    """
    help = None
    group = None
    arg = None

    @staticmethod
    def execute(**kwargs):
        raise NotImplementedError

    @classmethod
    def option(cls):
        """
        Derives the option string from the class name and returns it. All capital letters and lowered and prefixed
        with a dash except for the initial letter which has two dashes indicating an option.

        :rtype: str
        :return: option string derived from class name
        """
        from re import sub

        return "--{0}".format(sub(r"(\w)([A-Z])", r"\1-\2", cls.__name__).lower())
