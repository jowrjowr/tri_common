import common.database as _database
import common.logger as _logger
import models as _models

from commands import Command


class CreateTables(Command):
    __description__ = "Create all tables if they are not present."

    def __call__(self, arg, **kwargs):
        super(CreateTables, self).__call__(arg, **kwargs)

        _logger.debug("Creating SQL Tables.")
        _models.Base.metadata.create_all(bind=_database.engine())

        return kwargs
