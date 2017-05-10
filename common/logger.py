import enum as _enum
import logging as _logging
import sys as _sys
import time as _time
import argparse

class LogFormat(_enum.Enum):
    SIMPLE = 0
    TIMESTAMP = 1
    ADVANCED = 3


class LogLevel(_enum.Enum):
    DEBUG = _logging.DEBUG
    INFO = _logging.INFO
    WARNING = _logging.WARNING
    ERROR = _logging.ERROR
    CRITICAL = _logging.CRITICAL


class LogMode(_enum.Enum):
    SINGLE = 0
    DAILY = 1
    WEEKLY = 2
    MONTHLY = 3


def debug(message):
    log(message, LogLevel.DEBUG)

def init(log_dir="/srv/api/logs/", log_lvl=_logging.INFO, log_mod=LogMode.DAILY, log_fmt=LogFormat.TIMESTAMP, log_name=None):
    """
    Initialize logging facilities

    Configuration is either passed on in kwargs or otherwise read from a configuration file.
    The configuration file path can also be alternatively passed on as an argument.

    :param log_dir: directory to save the log files
    :param log_lvl: logging threshold
    :param log_mod: log file mode (see enum LogMode)
    :param log_fmt: log format (see enum LogFormat)
    :return:
    """

    # base logger
    logger = _logging.getLogger()
    logger.setLevel(log_lvl.value)

    # make sure log level is honored
    for log in _logging.Logger.manager.loggerDict:
        _logging.getLogger(log).setLevel(log_lvl.value)

    # setup log name
    if log_dir[-1] != "/":
        log_dir += "/"

    if log_name == None:
        log_name = _sys.argv[0].split('/')[-1].split('.')[0]

    log_file_fmt = log_dir + log_name + "{0}.log"

    if log_mod == LogMode.SINGLE:
        log_file_ins = ""
    elif log_mod == LogMode.DAILY:
        log_file_ins = _time.strftime("_%Y_%m_%d")
    elif log_mod == "weekly":
        log_file_ins = _time.strftime("_%Y_%W")
    elif log_mod == "monthly":
        log_file_ins = _time.strftime("_%Y_%m")
    else:
        raise TypeError("Argument log_mode is an invalid LogMode enum.")


    # setup output format
    if log_fmt == LogFormat.SIMPLE:
        log_out_fmt = "%(levelname)s: %(message)s"
    elif log_fmt == LogFormat.TIMESTAMP:
        log_out_fmt = "[%(asctime)s] %(levelname)s: %(message)s"
    elif log_fmt == LogFormat.ADVANCED:
        log_out_fmt = "[%(asctime)s | PID:%(process)d] %(levelname)s %(filename)s(%(lineno)d): %(message)s"
    else:
        raise TypeError("Argument log_fmt is an invalid LogFormat enum.")

    # setup file logger
    file_logger = _logging.FileHandler(log_file_fmt.format(log_file_ins), mode='a')
    file_logger.setLevel(log_lvl.value)
    file_logger.setFormatter(_logging.Formatter(log_out_fmt))
    logger.addHandler(file_logger)

    # setup stdout logger
    stdout_logger = _logging.StreamHandler(_sys.stdout)
    stdout_logger.setLevel(log_lvl.value)
    logger.addHandler(stdout_logger)

def log(message, log_lvl):
    logger = _logging.getLogger(__name__)
    logger.log(level=log_lvl.value, msg=message)

def LogSetup(log_lvl, log_name, log_dir):
    log_lvl = log_lvl.upper()

    # log to a specific filename prefix
    if log_name == None:
        log_name = _sys.argv[0].split('/')[-1].split('.')[0]

    init(
        log_lvl=LogLevel[log_lvl],
        log_mod=LogMode.DAILY,
        log_fmt=LogFormat.TIMESTAMP,
        log_name=log_name,
        log_dir=log_dir,
    )

class parseaction(argparse.Action):
    def __init__(self, option_strings, dest, nargs=None, **kwargs):
        if nargs is not None:
            raise ValueError("nargs not allowed")
        super(parseaction, self).__init__(option_strings, dest, **kwargs)
    def __call__(self, parser, namespace, values, option_string=None):
        setattr(namespace, self.dest, values)
        LogSetup(values)

class parseaction(argparse.Action):
    def __init__(self, option_strings, dest, nargs=None, **kwargs):
        if nargs is not None:
            raise ValueError("nargs not allowed")
        super(parseaction, self).__init__(option_strings, dest, **kwargs)
    def __call__(self, parser, namespace, values, option_string=None):
        setattr(namespace, self.dest, values)

def add_arguments(parser):

    parser.add_argument("--logname",
        dest='logname',
        default=None,
        help='prefix of log file name',
    )

    parser.add_argument("--logdir",
        dest='logdir',
        default="/srv/api/logs",
        help='logfile root directory',
    )

    parser.add_argument("--loglevel",
        dest='loglevel',
        choices=['debug', 'info', 'warning', 'error', 'critical'],
        default='info',
        help='log level',
    )

def securitylog(function, charid, ipaddress, action):
    # log stuff into the security table
    
    import MySQLdb as mysql
    import common.credentials.database as _database
    import common.logger as _logger
    from common.api import base_url
    import common.request_esi

    try:
        sql_conn = mysql.connect(
            database=_database.DB_DATABASE,
            user=_database.DB_USERNAME,
            password=_database.DB_PASSWORD,
            host=_database.DB_HOST)
    except mysql.Error as err:
        _logger.log('[' + __name__ + '] mysql error: ' + str(err), _logger.LogLevel.ERROR)
    cursor = sql_conn.cursor()
    
    # get character name
    esi_url = base_url + 'characters/{0}/?datasource=tranquility'.format(charid)
    code, result = common.request_esi.esi(__name__, esi_url, 'get')

    if not code == 200:
        _logger.log('[' + __name__ + '] /characters API error {0}: {1}'.format(code, result['error']), _logger.LogLevel.ERROR)
        return False
    try:
        charname = result['name']
    except KeyError as error:
        _logger.log('[' + __name__ + '] User does not exist: {0})'.format(charid), _logger.LogLevel.ERROR)
        charname = None
    
    # log to security table
    
    try:
        query = 'INSERT INTO Security (charID, charName, IP, action) VALUES(%s, %s, %s, %s, %s)'
        cursor.execute(query, (
            charid,
            charname,
            IP,
            action,
        ),)
    except mysql.Error as err:
        _logger.log('[' + __name__ + '] mysql error: ' + str(err), _logger.LogLevel.ERROR)
        return False
    finally:
        cursor.close()
        sql_conn.commit()
        sql_conn.close()
    return True

