#!/usr/bin/python3

import common.logger as _logger
import importlib as _importlib
import inspect as _inspect
import json as _json
import pkgutil as _pkgutil
import re as _re

from common.options import Options as _opts
import commands.audit.audit
import commands.maint.maint
import commands.forward.forward

def main():

    (options, args) = _opts.parser.parse_args()

if __name__ == '__main__':
    main()

