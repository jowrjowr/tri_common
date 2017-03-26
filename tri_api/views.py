from flask import Flask, request, url_for, json, Response
import json
from . import app
import tri_api.endpoints as _endpoints

def root():
    return Response(json.dumps({}), status=200, mimetype='application/json')
app.add_url_rule('/', 'root', root)
app.add_url_rule('/auth', 'root', root)

def hello_world():
    return 'hello world'
app.add_url_rule('/hello', 'hello', hello_world)
from tri_api.endpoints.core.structures import core_structures
app.add_url_rule('/core/structures', 'structures', core_structures)
from tri_api.endpoints.core.isblue import core_isblue
app.add_url_rule('/core/isblue', 'isblue', core_isblue)
from tri_api.endpoints.auth.spyregistration import auth_spyregister
from tri_api.endpoints.auth.spyregistration import auth_spyregister_callback
app.add_url_rule('/auth/5eyes/register', 'spyregister', auth_spyregister)
app.add_url_rule('/auth/5eyes/callback', 'spycallback', auth_spyregister_callback)
