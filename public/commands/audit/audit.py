import common.database as DATABASE
import common.logger as _logger
import models as _models
import random as _rnd
import string as _str
import MySQLdb as mysql

from commands import Command, InvalidArgument
from commands.audit.jabber import audit_jabber
from commands.audit.teamspeak import audit_teamspeak
from commands.audit.core import audit_core

class Audit(Command):
    __description__ = "Audit Tri core for users who have left the coalition"

    def __call__(self, arg, **kwargs):
        super(Audit, self).__call__(arg, **kwargs)

        _logger.log('[' + __name__ + '] core audit', _logger.LogLevel.DEBUG)
        audit_core()
        _logger.log('[' + __name__ + '] jabber audit', _logger.LogLevel.DEBUG)
        audit_jabber()
        _logger.log('[' + __name__ + '] teamspeak audit', _logger.LogLevel.DEBUG)
        audit_teamspeak()

        return kwargs
