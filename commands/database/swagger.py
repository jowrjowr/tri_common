from commands import Command


class SwaggerUpdate(Command):
    __description__ = "Update ESI Endpoints."

    def __call__(self, arg, **kwargs):
        super(SwaggerUpdate, self).__call__(arg, **kwargs)

        return kwargs
