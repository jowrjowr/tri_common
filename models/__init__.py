from .model import Model

from sqlalchemy.ext.declarative import declarative_base, declared_attr

Base = declarative_base()

from .api_user import APIUser
from .esi_endpoint import ESIEndpoint


class ModelException(Exception):
    pass


class ModelExists(ModelException):
    pass


class ModelNotFound(ModelException):
    pass


class InvalidArguments(ModelException):
    pass
