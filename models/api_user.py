import sqlalchemy as _sql

from models import Model, Base


class APIUser(Model, Base):
    token = _sql.Column(_sql.String(16), unique=True)
    groups = _sql.Column(_sql.Text)
