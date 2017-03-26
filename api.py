#!/usr/bin/python3

import argparse as _argparse
import common.logger as _logger
import endpoints as _endpoints
import importlib as _importlib
import inspect as _inspect
import json as _json
import pkgutil as _pkgutil

from flask import Flask, Blueprint, Response
app = Flask('tri_api')

def root():
    return Response(_json.dumps({}), status=200, mimetype='application/json')
app.add_url_rule('/', 'root', root)
app.add_url_rule('/auth', 'root', root)

def hello_world():
    return 'hello world'
app.add_url_rule('/hello', 'hello', hello_world)


def main():
    print('[DEBUG] loading main()')
    parser = _argparse.ArgumentParser()

    # logging options
    options_parser = parser.add_argument_group("options")
    options_parser.add_argument("--debug", action="store_true", default=False)
    options_parser.add_argument("--log-single", action="store_true", default=False)
    options_parser.add_argument("--log-verbose", action="store_true", default=False)
    options_parser.add_argument("--quiet", action="store_true", default=False)

    arguments = parser.parse_args()

    # initialize logging
    log_lvl = _logger.LogLevel.DEBUG
    log_mod = _logger.LogMode.DAILY
    log_fmt = _logger.LogFormat.SIMPLE

    if arguments.debug:
        log_lvl = _logger.LogLevel.DEBUG
    elif arguments.quiet:
        log_lvl = _logger.LogLevel.WARNING

    if arguments.log_single:
        log_mod = _logger.LogMode.SINGLE

    if arguments.log_verbose:
        log_fmt = _logger.LogFormat.TIMESTAMP

    _logger.init(log_lvl=log_lvl, log_mod=log_mod, log_fmt=log_fmt)

    # register all blueprints
    for _, modname, is_pkg in _pkgutil.iter_modules(_endpoints.__path__):
        if is_pkg:
            module = _importlib.import_module("endpoints." + modname)
            app.register_blueprint(getattr(module, 'blueprint'))



    from endpoints.core.structures import core_structures
    app.add_url_rule('/core/structures', 'structures', core_structures)
    from endpoints.core.isblue import core_isblue
    app.add_url_rule('/core/isblue', 'isblue', core_isblue)
    from endpoints.auth.spyregistration import auth_spyregister
    from endpoints.auth.spyregistration import auth_spyregister_callback
    app.add_url_rule('/auth/5eyes/register', 'spyregister', auth_spyregister)
    app.add_url_rule('/auth/5eyes/callback', 'spycallback', auth_spyregister_callback)
    print('[DEBUG] done loading main()')

if __name__ == '__main__':
    main()
    app.run('0.0.0.0',5000)


