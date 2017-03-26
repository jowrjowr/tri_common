#!/usr/bin/python3

from flask import Flask, Blueprint, Response
import os

app = Flask(__name__)

# secret_key is a random seed value for http sessions
app.secret_key = os.urandom(24)
# the transport to nginx is https but nginx<-->uwsgi is not

app.config.update({
    'OAUTH1_PROVIDER_ENFORCE_SSL': False
})
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

import tri_api.views



