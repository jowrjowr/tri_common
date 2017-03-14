import common.logger as _logger
import asyncio

from commands import Command, InvalidArgument
from commands.audit.jabber import audit_jabber
from commands.audit.teamspeak import audit_teamspeak
from commands.audit.core import audit_core
from commands.audit.coregroups import audit_coregroups
from commands.audit.bothunt import audit_bothunt
from common.options import Options as _opts

def audit_all():
    _logger.log('[' + __name__ + '] core audit', _logger.LogLevel.DEBUG)
    audit_core()
    _logger.log('[' + __name__ + '] jabber audit', _logger.LogLevel.DEBUG)
    audit_jabber()
    _logger.log('[' + __name__ + '] teamspeak audit', _logger.LogLevel.DEBUG)
    audit_teamspeak()
    _logger.log('[' + __name__ + '] core group audit', _logger.LogLevel.DEBUG)
    audit_coregroups()
    _logger.log('[' + __name__ + '] jabber bothunt', _logger.LogLevel.DEBUG)
    audit_bothunt()

def auditing(option, opt_str, value, parser):
    if value == 'all':
        audit_all()
    elif value == 'jabber':
        audit_jabber()
    elif value == 'teamspeak':
        audit_teamspeak()
    elif value == 'core':
        audit_core()
    elif value == 'coregroups':
        audit_coregroups()
    elif value == 'bothunt':
        audit_bothunt()


_opts.parser.add_option('--audit',
    type='choice',
    action='callback',
    dest='audit_target',
    choices=['jabber','teamspeak','core','coregroups','bothunt','all'],
    default='all',
    help='core service auditing: jabber, teamspeak, core, coregroups, bothunt, all',
    callback=auditing,
)
