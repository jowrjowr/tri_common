from .model import Model

from sqlalchemy.ext.declarative import declarative_base, declared_attr

Base = declarative_base()

from .api_user import APIUser


class ModelException(Exception):
    pass


class ModelExists(ModelException):
    pass


class ModelNotFound(ModelException):
    pass
