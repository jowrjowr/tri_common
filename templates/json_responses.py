import json as _json

from flask import Response


def response_200(status, payload=None):
    return Response(_json.dumps({'status': status,
                                 'payload': payload}),
                    status=200, mimetype='application/json')

def response_400(error="Bad request"):
    return Response(_json.dumps({'error': error}), status=400, mimetype='application/json')


def response_401(error="Unauthorized"):
    return Response(_json.dumps({'error': error}), status=401, mimetype='application/json')


def response_403(error="Forbidden"):
    return Response(_json.dumps({'error': error}), status=403, mimetype='application/json')


def response_404(error="Not found"):
    return Response(_json.dumps({'error': error}), status=404, mimetype='application/json')


def response_500(error="Internal server error"):
    return Response(_json.dumps({'error': error}), status=500, mimetype='application/json')


def response_501(error="Not implemented"):
    return Response(_json.dumps({'error': error}), status=500, mimetype='application/json')
