#!/usr/bin/python3

import argparse as _argparse
import common.logger as _logger
import endpoints as _endpoints
import importlib as _importlib
import inspect as _inspect
import json as _json
import pkgutil as _pkgutil

from flask import Flask, Blueprint, Response
app = Flask(__name__)


@app.route("/")
def root():
    return Response(_json.dumps({}), status=200, mimetype='application/json')


def main():
    parser = _argparse.ArgumentParser()

    # logging options
    options_parser = parser.add_argument_group("options")
    options_parser.add_argument("--debug", action="store_true", default=False)
    options_parser.add_argument("--log-single", action="store_true", default=False)
    options_parser.add_argument("--log-verbose", action="store_true", default=False)
    options_parser.add_argument("--verbose", action="store_true", default=False)

    arguments = parser.parse_args()

    # initialize logging
    log_lvl = _logger.LogLevel.INFO
    log_mod = _logger.LogMode.DAILY
    log_fmt = _logger.LogFormat.SIMPLE

    if arguments.debug:
        log_lvl = _logger.LogLevel.DEBUG

    if arguments.log_single:
        log_mod = _logger.LogMode.SINGLE

    if arguments.log_verbose:
        log_fmt = _logger.LogFormat.TIMESTAMP

    _logger.init(log_lvl=log_lvl, log_mod=log_mod, log_fmt=log_fmt)

    # register all blueprints
    for _, modname, is_pkg in _pkgutil.iter_modules(_endpoints.__path__):
        if is_pkg:
            module = _importlib.import_module("endpoints." + modname)
            print("registering "+modname)
            print(getattr(module, 'blueprint'))
            app.register_blueprint(getattr(module, 'blueprint'))


if __name__ == '__main__':
    main()
    app.run()
