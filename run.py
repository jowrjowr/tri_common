#!/usr/bin/python3

import common.logger as _logger
import importlib as _importlib
import inspect as _inspect
import json as _json
import pkgutil as _pkgutil
import re as _re

import commands.audit.audit
import commands.maint.maint
import commands.forward.forward
import argparse

def main():

    parser = argparse.ArgumentParser()
    parser.add_argument("--loglevel",
        action='store',
        dest='loglevel',
        choices=['debug', 'info', 'warning', 'error', 'critical'],
        default='info',
        help='Level of log output (default is info)',
    )

if __name__ == '__main__':
    main()

