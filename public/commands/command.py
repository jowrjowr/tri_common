class Command:
    __description__ = None

    __metavar__ = None
    __metavar_require__ = False

    __kwargs_require__ = {}

    def __call__(self, arg, **kwargs):
        for key in self.__kwargs_require__:
            if key not in kwargs:
                raise KeyError("Command {0} __call__ aborted as the key {1} was not passed."
                               .format(self.__class__.__name__, key))
