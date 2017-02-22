import common.database as _database
import common.logger as _logger
import models as _models
import random as _rnd
import string as _str

from commands import Command, InvalidArgument
from models.api_user import APIUser


class AddUser(Command):
    __description__ = "Add user."
    __metavar__ = "USERNAME"
    __metavar_require__ = True

    def __call__(self, arg, **kwargs):
        super(AddUser, self).__call__(arg, **kwargs)

        # verify that name is valid (only contains characters or underscores)
        if not str(arg).replace("_", "").isalpha():
            error = "Attempt to add api_user \"{0}\" failed as username contains illegal characters.".format(arg)
            _logger.log(error, _logger.LogLevel.ERROR)
            raise InvalidArgument(error)

        session = _database.session()

        # verify that user doesn't already exist with same name
        conflict_user = session.query(APIUser).filter(APIUser.name == arg).first()
        if conflict_user is not None:
            error = "Attempt to add api_user \"{0}\" failed as user already exists.".format(arg)
            _logger.log(error, _logger.LogLevel.ERROR)
            raise _models.ModelExists(error)

        # generate token and resolve collision
        user_token = ''.join(_rnd.choices(_str.ascii_letters + _str.digits, k=16))
        while session.query(APIUser).filter(APIUser.token == user_token).first() is not None:
            user_token = ''.join(_rnd.choices(_str.ascii_letters + _str.digits, k=16))

        # empty groups
        user_groups = "{}"

        user = APIUser()

        user.name = arg
        user.token = user_token
        user.groups = user_groups

        try:
            session.add(user)
            session.commit()
        except Exception as e:
            error = "Failed to add api_user {0} due to an unhandled exception: {1}.".format(arg, e)
            _logger.log(error, _logger.LogLevel.ERROR)
            raise

        # get new user id and add to kwargs
        user = session.query(APIUser).filter(APIUser.name == arg).first()
        kwargs['user'] = user.id

        session.close()

        return kwargs
