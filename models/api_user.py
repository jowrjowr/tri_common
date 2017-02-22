import enum as _enum
import models as _models
import sqlalchemy as _sql

from models import Base, Model


class APIUser(Model, Base):
    token = _sql.Column(_sql.String(16), unique=True)
    groups = _sql.Column(_sql.Text)
