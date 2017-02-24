import sqlalchemy as _sql

from sqlalchemy.ext.declarative import declared_attr


class Model(object):
    @declared_attr
    def __tablename__(cls):
        caps = -1
        for letter in cls.__name__:
            if letter.islower():
                break

            caps += 1

        return cls.__name__.lower()[:caps] + "_" + cls.__name__.lower()[caps:] + "s"

    __table_args__ = {'mysql_engine': 'InnoDB'}
    __mapper_args__ = {'always_refresh': True}

    id = _sql.Column(_sql.Integer, primary_key=True, autoincrement=True)
    name = _sql.Column(_sql.String(64), index=True, unique=True)
