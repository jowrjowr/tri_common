import common.logger as _logger
import asyncio
import argparse

from commands.audit.jabber import audit_jabber
from commands.audit.teamspeak import audit_teamspeak
from commands.audit.core import audit_core
from commands.audit.bothunt import audit_bothunt
from commands.audit.forums import audit_forums
from commands.audit.supers import audit_supers

def audit_all():
    _logger.log('[' + __name__ + '] core audit', _logger.LogLevel.DEBUG)
    audit_core()
    _logger.log('[' + __name__ + '] jabber audit', _logger.LogLevel.DEBUG)
    audit_jabber()
    _logger.log('[' + __name__ + '] teamspeak audit', _logger.LogLevel.DEBUG)
    audit_teamspeak()
    #_logger.log('[' + __name__ + '] jabber bothunt', _logger.LogLevel.DEBUG)
    #audit_bothunt()

class parseaction(argparse.Action):
    def __init__(self, option_strings, dest, nargs=None, **kwargs):
       # if nargs is not None:
        #    raise ValueError("nargs not allowed")
        super(parseaction, self).__init__(option_strings, dest, **kwargs)
    def __call__(self, parser, namespace, value, option_string=None):
        setattr(namespace, self.dest, value)

        # setup logging
        if namespace.logname == None:
            filename = "maint"
        else:
            filename = namespace.logname

        _logger.LogSetup(namespace.loglevel, filename, namespace.logdir)

        # do actual things

        if value == 'all':
            audit_all()
        elif value == 'jabber':
            audit_jabber()
        elif value == 'teamspeak':
            audit_teamspeak()
        elif value == 'core':
            audit_core()
        elif value == 'bothunt':
            audit_bothunt()
        elif value == 'forums':
            audit_forums()
        elif value == 'supers':
            audit_supers()

def add_arguments(parser):
    parser.add_argument("--audit",
        nargs=0,
        action=parseaction,
        choices=[ 'jabber', 'teamspeak', 'core', 'coregroups', 'forums', 'bothunt', 'supers', 'all' ],
        help='core service auditing',
    )
