#!/usr/bin/python3

import common.logger as _logger
import importlib as _importlib
import inspect as _inspect
import json as _json
import pkgutil as _pkgutil
import re as _re

from common.options import Options as _opts
import commands.audit.audit



def main():

    #import commands.audit.audit


    (options, args) = _opts.parser.parse_args()
    print(options)
    log_lvl = _logger.LogLevel.DEBUG
    _logger.init(
        log_lvl=_logger.LogLevel(log_lvl),
        log_mod=_logger.LogMode.DAILY,
        log_fmt=_logger.LogFormat.TIMESTAMP
    )
#    print(options)
#    print(args)

#    _logger.init(log_lvl=log_lvl, log_mod=log_mod, log_fmt=log_fmt)

if __name__ == '__main__':
    main()

