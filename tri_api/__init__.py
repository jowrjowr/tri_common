#!/usr/bin/python3

from flask import Flask, Blueprint, Response
import common.logger as _logger
import os
import argparse

app = Flask(__name__)
parser = argparse.ArgumentParser()
parser.add_argument("--loglevel",
    action='store',
    dest='loglevel',
    choices=['debug', 'info', 'warning', 'error', 'critical'],
    default='info',
    help='Level of log output (default is info)',
)
arguments = parser.parse_args()
# initialize logging
_logger.LogSetup(arguments.loglevel)
# secret_key is a random seed value for http sessions
app.secret_key = os.urandom(24)
# the transport to nginx is https but nginx<-->uwsgi is not

app.config.update({
    'OAUTH1_PROVIDER_ENFORCE_SSL': False
})
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

import tri_api.views



