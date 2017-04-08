#!/usr/bin/python3

import common.logger as _logger
import importlib as _importlib
import inspect as _inspect
import json as _json
import pkgutil as _pkgutil
import re as _re

import commands.audit.audit as _audit
import commands.maint.maint as _maint
import commands.forward.forward as _forward
import argparse

def main():

    parser = argparse.ArgumentParser()
    _maint.add_arguments(parser)
    _logger.add_arguments(parser)
    _forward.add_arguments(parser)
    _audit.add_arguments(parser)

    arguments = parser.parse_args()

if __name__ == '__main__':
    main()

