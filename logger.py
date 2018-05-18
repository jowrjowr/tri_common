import enum as _enum
import logging as _logging
import sys as _sys
import time as _time
import argparse
import logging
import time
import sys
import urllib

import MySQLdb as mysql
import common.request_esi
import common.credentials.database as _database
from enum import Enum
from sys import stdout as STDOUT
from logging.handlers import TimedRotatingFileHandler

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

def securitylog(function, action, charid=None, charname=None, ipaddress=None, date=None, detail=None):
    # log stuff into the security table

    import MySQLdb as mysql
    import common.credentials.database as _database
    import common.esihelpers as _esihelpers
    import common.logger as _logger
    import common.request_esi
    import time
    import urllib

    if date == None:
        date = time.time()

    friendly_time = time.asctime( time.localtime(date) )

    # mysql logging

    try:
        sql_conn = mysql.connect(
            database=_database.DB_DATABASE,
            user=_database.DB_USERNAME,
            password=_database.DB_PASSWORD,
            host=_database.DB_HOST)
    except mysql.Error as err:
        _logger.log('[' + __name__ + '] mysql error: ' + str(err), _logger.LogLevel.ERROR)
    cursor = sql_conn.cursor()

    # try to get character id if a charname (but no charid) is supplied

    if not charname == None and charid == None:
        query = { 'categories': 'character', 'datasource': 'tranquility', 'language': 'en-us', 'search': charname, 'strict': 'true' }
        query = urllib.parse.urlencode(query)
        esi_url = 'search/?' + query
        code, result = common.request_esi.esi(__name__, esi_url, 'get')

        # not going to hardfail here, search is fuzzier than other endpoints

        try:
            charid = result['character'][0]
        except KeyError as error:
            _logger.log('[' + function + '] unable to identify charname: {0}'.format(charname), _logger.LogLevel.WARNING)
            charid = None


    # try to get character name if a charid (but no charname) is supplied
    if charname == None and not charid == None:
        affiliations = _esihelpers.esi_affiliations(charid)
        charname = affiliations.get('charname')

    # log to file

    _logger.log('[{0}] {1}: {2} ({3}) @ {4} {5}: {6}'.format(function, friendly_time, charname, charid, ipaddress, action, detail),_logger.LogLevel.INFO)

    # log to security table

    try:
        query = 'INSERT INTO Security (charID, charName, IP, action, date, detail) VALUES(%s, %s, %s, %s, FROM_UNIXTIME(%s), %s)'
        cursor.execute(query, (
            charid,
            charname,
            ipaddress,
            action,
            date,
            detail,
        ),)
    except mysql.Error as err:
        _logger.log('[' + __name__ + '] mysql error: ' + str(err), _logger.LogLevel.ERROR)
        return False
    finally:
        cursor.close()
        sql_conn.commit()
        sql_conn.close()
    return True


##############
# new logging setup. massive pain in the ass to convert.
# easier to just put in new functions and import as standard names and slowly convert

def LogLevel_new(log_lvl):

    if log_lvl == 'DEBUG': return logging.DEBUG
    if log_lvl == 'INFO': return logging.INFO
    if log_lvl == 'WARNING': return logging.WARNING
    if log_lvl == 'ERROR': return logging.ERROR
    if log_lvl == 'CRITICAL': return logging.CRITICAL

    return logging.INFO

def getlogger_new(log_name=__name__):

    # configure the root logger and handlers with default of info

    log_level = logging.INFO
    log_dir = 'logs/'

    # build out the log format

    log_fmt_str = "[%(asctime)s] [%(process)d] [%(threadName)s] [%(name)s] %(levelname)s: %(message)s"
    log_fmt = logging.Formatter(log_fmt_str)

    ## logging stream handlers:

    # STDOUT - use the same log level

    log_stdout = logging.StreamHandler(STDOUT)
    log_stdout.setLevel(log_level)
    log_stdout.setFormatter(log_fmt)

    # file output that rotates. same log level as STDOUT

    log_file = TimedRotatingFileHandler(
        log_dir + log_name,
        when='midnight',
        backupCount=14,
        utc=True,
    )
    log_file.suffix = "_%Y_%m_%d"
    log_file.setLevel(log_level)
    log_file.setFormatter(log_fmt)

    # short term debug output that rotates every day

    log_file_debug = TimedRotatingFileHandler(
        log_dir + 'debug_' + log_name,
        when='midnight',
        backupCount=0,
        utc=True,
    )
    log_file_debug.setLevel(logging.DEBUG)
    log_file_debug.setFormatter(log_fmt)

    # set the root logger

    logger = logging.getLogger(log_name)
    logger.addHandler(log_stdout)
    logger.addHandler(log_file)
    logger.addHandler(log_file_debug)
    logger.setLevel(logging.DEBUG)

    return logger

def securitylog_new(action, threaded=False, charid=None, charname=None, ipaddress=None, date=None, detail=None):

    # log stuff into the security table

    function = stack()[1][3]
    log_name = + 'securitylog' + '_' + function
    logger = getlogger(log_name=log_name, threaded=threaded)

    if date == None:
        date = time.time()

    friendly_time = time.asctime( time.localtime(date) )

    # mysql logging

    try:
        sql_conn = mysql.connect(
            database=_database.DB_DATABASE,
            user=_database.DB_USERNAME,
            password=_database.DB_PASSWORD,
            host=_database.DB_HOST)
    except mysql.Error as err:
        msg = 'mysql error: {0}'.format(err)
        logger.critical(msg)
        cursor = sql_conn.cursor()

    # try to get character id if a charname (but no charid) is supplied

    if not charname == None and charid == None:
        query = { 'categories': 'character', 'datasource': 'tranquility', 'language': 'en-us', 'search': charname, 'strict': 'true' }
        query = urllib.parse.urlencode(query)
        esi_url = 'search/?' + query
        code, result = common.request_esi.esi(__name__, esi_url, 'get')

        msg = 'search result code: {0} result: {1}'.format(code, result)
        logger.debug(msg)

        # not going to hardfail here, search is fuzzier than other endpoints

        try:
            charid = result['character'][0]
        except KeyError as error:
            msg = 'unable to identify charname: {0}'.format(charname)
            logger.warning(msg)
            charid = None

    # try to get character name if a charid (but no charname) is supplied
    if charname == None and not charid == None:
        esi_url = 'characters/{0}/?datasource=tranquility'.format(charid)
        code, result = common.request_esi.esi(__name__, esi_url, 'get')

        if code == 404:
            msg = 'character id {0} not found'.format(charid)
            logging.warning(msg)
            return False
        elif not code == 200:
            msg = '/characters API error {0}: {1}'.format(code, result['error'])
            logging.error(msg)
            return False
        try:
            charname = result['name']
        except KeyError as error:
            msg = 'User does not exist: {0})'.format(charid)
            logging.error(msg)
            charname = None


    msg = 'security log for charid {0} / charname {1} @ ip {2} on date {3}'.format(charid, charname, ipaddress, date)
    logger.info(msg)
    msg = 'action: {0} detail {1}'.format(action, detail)
    logger.info(msg)

    # log to security table

    try:
        query = 'INSERT INTO Security (charID, charName, IP, action, date, detail) VALUES(%s, %s, %s, %s, FROM_UNIXTIME(%s), %s)'
        cursor.execute(query, (
            charid,
            charname,
            ipaddress,
            action,
            date,
            detail,
        ),)
    except mysql.Error as err:
        msg = 'mysql error: {0}'.format(err)
        logger.error(msg)
        return False
    finally:
        cursor.close()
        sql_conn.commit()
        sql_conn.close()
    return True


def getlogger_new(log_name=__name__):

    # configure the root logger and handlers with default of info

    log_level = logging.INFO
    log_dir = 'logs/'

    # build out the log format

    log_fmt_str = "[%(asctime)s] [%(process)d] [%(threadName)s] [%(name)s] %(levelname)s: %(message)s"
    log_fmt = logging.Formatter(log_fmt_str)

    ## logging stream handlers:

    # STDOUT - use the same log level

    log_stdout = logging.StreamHandler(STDOUT)
    log_stdout.setLevel(log_level)
    log_stdout.setFormatter(log_fmt)

    # file output that rotates. same log level as STDOUT

    log_file = TimedRotatingFileHandler(
        log_dir + log_name,
        when='midnight',
        backupCount=14,
        utc=True,
    )
    log_file.suffix = "_%Y_%m_%d"
    log_file.setLevel(log_level)
    log_file.setFormatter(log_fmt)

    # short term debug output that rotates every day

    log_file_debug = TimedRotatingFileHandler(
        log_dir + 'debug_' + log_name,
        when='midnight',
        backupCount=0,
        utc=True,
    )
    log_file_debug.setLevel(logging.DEBUG)
    log_file_debug.setFormatter(log_fmt)

    # set the root logger

    logger = logging.getLogger(log_name)
    logger.addHandler(log_stdout)
    logger.addHandler(log_file)
    logger.addHandler(log_file_debug)
    logger.setLevel(logging.DEBUG)

    return logger

