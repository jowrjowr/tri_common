from flask import Flask, request, url_for, json, Response
import json
from . import app
import tri_api.endpoints
import tri_core.endpoints

def root():
    return Response(json.dumps({}), status=200, mimetype='application/json')
app.add_url_rule('/', 'root', root)
app.add_url_rule('/auth', 'root', root)

def hello_world():
    return 'hello world'
app.add_url_rule('/hello', 'hello', hello_world)


from tri_core.pages.main import page_main
app.add_url_rule('/pages/', 'main', page_main)
app.add_url_rule('/pages/main', 'main', page_main)
from tri_core.pages.blacklist import page_blacklist
app.add_url_rule('/pages/blacklist', 'blacklist', page_blacklist)

