from commands.maint.tokens import maint_tokens
import common.logger as _logger
import argparse

# do everything
def maint_all():
    maint_tokens()

class parseaction(argparse.Action):
    def __init__(self, option_strings, dest, nargs=None, **kwargs):
        if nargs is not None:
            raise ValueError("nargs not allowed")
        super(parseaction, self).__init__(option_strings, dest, **kwargs)
    def __call__(self, parser, namespace, values, option_string=None):
        setattr(namespace, self.dest, values)
        if values == 'all':
            _logger.log('[' + __name__ + '] token maintenance', _logger.LogLevel.INFO)
            maint_all()
        elif values == 'tokens':
            _logger.log('[' + __name__ + '] token maintenance', _logger.LogLevel.INFO)
            maint_tokens()


def add_arguments(parser):
    parser.add_argument("--maint",
        dest='maint_target',
        choices=['tokens', 'all'],
        default='all',
        action=parseaction,
        help='core maintenance commands',
    )

