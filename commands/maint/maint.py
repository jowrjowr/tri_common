import common.logger as _logger
import asyncio

from commands import Command, InvalidArgument
from common.options import Options as _opts
from commands.maint.tokens import maint_tokens

def maint_all():
    pass

def maint(option, opt_str, value, parser):
    if value == 'all':
        _logger.log('[' + __name__ + '] token maintenance', _logger.LogLevel.DEBUG)
        maint_all()
    elif value == 'tokens':
        maint_tokens()

_opts.parser.add_option('--maint',
    type='choice',
    action='callback',
    dest='maint_target',
    choices=['tokens','all'],
    default='all',
    help='core maintenance commands: tokens, all',
    callback=maint,
)
