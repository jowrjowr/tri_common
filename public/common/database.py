import common.logger as _logger
import configparser as _configparser
import sqlalchemy as _sql
import sqlalchemy.orm as _orm


def engine(cfg_dir="storage/config/"):
    configfile = _configparser.ConfigParser()

    # attempt to open config file
    try:
        configfile.read(cfg_dir + "database.ini")
        sql_config = configfile["DATABASE"]

        database = sql_config.get("DATABASE")
        username = sql_config.get("USERNAME")
        password = sql_config.get("PASSWORD")
    except KeyError:
        critical = "Configuration file config.conf could not be found or missing the SQL section."
        _logger.log(critical, _logger.LogLevel.CRITICAL)
        raise FileNotFoundError(critical)

    # database url
    return _sql.create_engine("mysql+pymysql://{0}:{1}@localhost:3306/{2}?charset=utf8"
                              .format(username, password, database))


def session(cfg_dir="storage/config/"):
    return _orm.sessionmaker(bind=engine(cfg_dir))()
