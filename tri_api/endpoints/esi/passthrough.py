from flask import request
from tri_api import app

@app.route('/core/esi/<path:url>', methods=['GET', 'POST'])
def core_esi_passthrough(url):

    from flask import Flask, request, url_for, json, Response
    from common.api import base_url
    import common.credentials.ldap as _ldap
    import common.request_esi
    import common.logger as _logger
    import ldap
    import json
    import urllib

    # a wrapper around standard ESI requests for things like php core

    if 'id' not in request.args:
        _logger.log('[' + __name__ + '] no id parameter', _logger.LogLevel.WARNING)
        js = json.dumps({ 'error': 'need an id to authenticate using'})
        resp = Response(js, status=401, mimetype='application/json')
        return resp

    try:
        id = int(request.args['id'])
    except ValueError:
        _logger.log('[' + __name__ + '] invalid id: "{0}"'.format(request.args['id']), _logger.LogLevel.WARNING)
        js = json.dumps({ 'error': 'id parameter must be integer'})
        resp = Response(js, status=401, mimetype='application/json')
        return resp

    # make a copy of the parameters

    parameters = dict()
    for key in request.args:
        parameters[key] = request.args[key]

    # the id parameter is just something i use internally
    del(parameters['id'])

    _logger.log('[' + __name__ + '] esi passthrough request for charid {0}: {1}'.format(request.args['id'], url), _logger.LogLevel.DEBUG)

    # snag the user's ldap token

    ldap_conn = ldap.initialize(_ldap.ldap_host, bytes_mode=False)
    try:
        ldap_conn.simple_bind_s(_ldap.admin_dn, _ldap.admin_dn_password)
    except ldap.LDAPError as error:
        _logger.log('[' + __name__ + '] LDAP connection error: {}'.format(error),_logger.LogLevel.ERROR)
        js = json.dumps({ 'error': 'internal ldap error'})
        resp = Response(js, status=500, mimetype='application/json')
        return resp

    try:
        result = ldap_conn.search_s('ou=People,dc=triumvirate,dc=rocks', ldap.SCOPE_SUBTREE, filterstr='(&(objectclass=pilot)(uid={0}))'.format(id), attrlist=['esiAccessToken'])
        user_count = result.__len__()
    except ldap.LDAPError as error:
        _logger.log('[' + __name__ + '] unable to fetch ldap information: {}'.format(error),_logger.LogLevel.ERROR)
        js = json.dumps({ 'error': 'internal ldap error'})
        resp = Response(js, status=500, mimetype='application/json')
        return resp
    # this shouldn't happen often tbh
    if user_count == 0:
        js = json.dumps({ 'error': 'no id for uid'.format(id)})
        resp = Response(js, status=404, mimetype='application/json')
        return resp

    dn, atoken = result[0]
    atoken = atoken['esiAccessToken'][0].decode('utf-8')

    # add the token to the parameters

    parameters['token'] = atoken
    parameterstring = urllib.parse.urlencode(parameters)

    # we're going to just pass the request through with the access token attached

    esi_url = base_url + url + '?' + parameterstring
    print(esi_url)
    code, result = common.request_esi.esi(__name__, esi_url, 'get')
    resp = Response(json.dumps(result), status=code, mimetype='application/json')
    return resp
