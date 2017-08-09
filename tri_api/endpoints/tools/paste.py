from flask import request
from tri_api import app


@app.route('/tools/paste/', methods=['POST'])
def tools_paste_post():
    from flask import request, Response

    import common.logger as _logger
    import common.ldaphelpers as _ldaphelpers

    import json
    import flask
    import redis

    import binascii
    import os

    r = redis.StrictRedis(host='localhost', port=6379, db=0)

    key = binascii.b2a_hex(os.urandom(4)).decode('utf-8')

    while r.exists(key):
        key = binascii.b2a_hex(os.urandom(4)).decode('utf-8')

    data = flask.request.get_json()

    # process data here

    r.set('PASTE_{0}'.format(key), json.dumps(data))

    return flask.Response(json.dumps({'key': key}), status=200, mimetype='application/json')


@app.route('/tools/paste/<key>/<character_id>/', methods=['GET'])
def tools_paste_get(key, character_id=None):
    from flask import request, Response

    import common.logger as _logger
    import common.ldaphelpers as _ldaphelpers

    import json
    import flask
    import redis
    r = redis.StrictRedis(host='localhost', port=6379, db=0)

    if not r.exists('PASTE_{0}'.format(key)):
        flask.abort(404)

    data = r.get('PASTE_{0}'.format(key))

    if character_id is None:
        if data['scope'] != "public":
            return flask.Response(json.dumps({'error': "forbidden"}), status=403, mimetype='application/json')
    else:
        # get auth groups
        dn = 'ou=People,dc=triumvirate,dc=rocks'

        code, result = _ldaphelpers.ldap_search(__name__, dn, '(uid={})'.format(character_id), ['authGroup'])

        if code == 'error':
            error = 'unable to check auth groups roles for {0}: ({1}) {2}'.format(character_id, code, result)
            _logger.log('[' + __name__ + ']' + error, _logger.LogLevel.ERROR)
            js = json.dumps({'error': error})
            resp = Response(js, status=500, mimetype='application/json')
            return resp

        if result == None:
            msg = 'charid {0} not in ldap'.format(character_id)
            _logger.log('[' + __name__ + '] {}'.format(msg), _logger.LogLevel.ERROR)
            js = json.dumps({'error': msg})
            return Response(js, status=404, mimetype='application/json')

        (_, result), = result.items()

        if data['scope'] not in result['authGroup']:
            return flask.Response(json.dumps({'error': "forbidden"}), status=403, mimetype='application/json')

    return flask.Response(data, status=200, mimetype='application/json')
