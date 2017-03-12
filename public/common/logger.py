import configparser as _configparser
import enum as _enum
import logging as _logging
import sys as _sys
import time as _time


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


def init(log_dir="/srv/api/public/storage/logs/", log_lvl=_logging.INFO, log_mod=LogMode.DAILY, log_fmt=LogFormat.TIMESTAMP):
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

    # setup log name
    if log_dir[-1] != "/":
        log_dir += "/"

    scriptname = _sys.argv[0].split('/')[-1].split('.')[0]
    print(scriptname)
    log_file_fmt = log_dir + scriptname + "{0}.log"

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

    # setup base logger
    logger = _logging.getLogger()
    logger.setLevel(log_lvl.value)

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
