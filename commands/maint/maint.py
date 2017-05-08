from commands.maint.tokens import maint_tokens
from commands.maint.ldapgroups import maint_ldapgroups
from commands.maint.strikes import reset_strikes

import common.logger as _logger
import argparse

# do everything
def maint_all():
    _logger.log('[' + __name__ + '] ldap group maintenance', _logger.LogLevel.INFO)
    maint_ldapgroups()
    _logger.log('[' + __name__ + '] token maintenance', _logger.LogLevel.INFO)
    maint_tokens()

class parseaction(argparse.Action):
    def __init__(self, option_strings, dest, nargs=None, **kwargs):
        if nargs is not None:
            raise ValueError("nargs not allowed")
        super(parseaction, self).__init__(option_strings, dest, **kwargs)
    def __call__(self, parser, namespace, values, option_string=None):
        setattr(namespace, self.dest, values)

        # setup logging
        if namespace.logname == None:
            filename = "maint"
        else:
            filename = namespace.logname

        _logger.LogSetup(namespace.loglevel, filename, namespace.logdir)
        # actually do things

        if values == 'all':
            maint_all()
        elif values == 'tokens':
            _logger.log('[' + __name__ + '] token maintenance', _logger.LogLevel.INFO)
            maint_tokens()
        elif values == 'ldapgroups':
            _logger.log('[' + __name__ + '] ldap group maintenance', _logger.LogLevel.INFO)
            maint_ldapgroups()
        elif values == 'strikes':
            _logger.log('[' + __name__ + '] resetting user strikes', _logger.LogLevel.INFO)
            reset_strikes()


def add_arguments(parser):
    parser.add_argument("--maint",
        dest='maint_target',
        choices=['tokens', 'ldapgroups', 'all', 'strikes'],
        default='all',
        action=parseaction,
        help='core maintenance commands',
    )

