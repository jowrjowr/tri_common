import common.logger as _logger
from optparse import OptionParser
# need to initialize this as a class to access it everywhere

class Options():
    parser = OptionParser()
    parser.add_option("--loglevel",
        type='choice',
        action='callback',
        dest='loglevel',
        choices=['debug', 'info', 'warning', 'error', 'critical'],
        default='info',
        help='Level of log output (default is info)',
        callback=_logger.LogSetup
    )
