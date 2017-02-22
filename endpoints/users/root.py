import json as _json
import flask as _flask

from . import blueprint


@blueprint.route("/test")
def root():
    return _flask.Response(_json.dumps({'error': 'not implemented'}),
                           status=500, mimetype='application/json')
