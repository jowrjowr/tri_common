from flask import request
from tri_api import app

@app.route('/core/allianceaudit/<charid>', methods=[ 'GET' ])
def core_allianceaudit(charid):

    from flask import request, Response
    from concurrent.futures import ThreadPoolExecutor, as_completed
    from common.check_role import check_role
    import common.ldaphelpers as _ldaphelpers
    import common.logger as _logger
    import common.request_esi
    import json

    # do a corp level audit of who has services

    ipaddress = request.headers['X-Real-Ip']
    log_charid = request.args.get('log_charid')

    _logger.securitylog(__name__, 'corp audit information request', ipaddress=ipaddress, charid=log_charid)

    try:
        charid = int(charid)
    except ValueError:
        _logger.log('[' + __name__ + '] charid parameters must be integer: {0}'.format(charid),
                    _logger.LogLevel.WARNING)
        js = json.dumps({'error': 'charid parameter must be integer'})
        resp = Response(js, status=401, mimetype='application/json')
        return resp

    # check for auth groups

    allowed_roles = ['tsadmin']
    dn = 'ou=People,dc=triumvirate,dc=rocks'

    code, result = _ldaphelpers.ldap_search(__name__, dn, '(uid={})'.format(charid), ['authGroup'])

    if code == 'error':
        error = 'unable to check auth groups roles for {0}: ({1}) {2}'.format(charid, code, result)
        _logger.log('[' + __name__ + ']' + error,_logger.LogLevel.ERROR)
        js = json.dumps({ 'error': error})
        resp = Response(js, status=500, mimetype='application/json')
        return resp

    if result == None:
        msg = 'charid {0} not in ldap'.format(charid)
        _logger.log('[' + __name__ + '] {}'.format(msg),_logger.LogLevel.ERROR)
        js = json.dumps({ 'error': msg })
        return Response(js, status=404, mimetype='application/json')

    (_, result), = result.items()

    if not "tsadmin" in result['authGroup']:
        error = 'insufficient corporate roles to access this endpoint.'
        _logger.log('[' + __name__ + '] ' + error, _logger.LogLevel.INFO)
        js = json.dumps({'error': error})
        resp = Response(js, status=403, mimetype='application/json')
        return resp

    # get all entires for triumvirate
    code, result = _ldaphelpers.ldap_search(__name__, dn, 'alliance=933731581',
                                            ['uid', 'corporation', 'esiAccessToken'])

    if code == 'error':
        error = 'unable to fetch all tri ldap entries: ({0}) {1}'.format(code, result)
        _logger.log('[' + __name__ + ']' + error,_logger.LogLevel.ERROR)
        js = json.dumps({ 'error': error})
        resp = Response(js, status=500, mimetype='application/json')
        return resp

    corp_dict = {'corps': {}, 'statistics': {}}

    for entry in result:
        (_, result), = entry

        corp_id = result['corporation']

        if corp_id not in corp_dict['corps']:
            request_url = 'corporations/{}/?datasource=tranquility'.format(corp_id)
            esi_code, esi_result = common.request_esi.esi(__name__, request_url, method='get')

            if not code == 200:
                # something broke severely
                _logger.log('[' + __name__ + '] affiliations API error {0}: {1}'.format(code, result['error']),
                            _logger.LogLevel.ERROR)
                error = result['error']
                result = {'code': code, 'error': error}
                return code, result

            corp_dict['corps'][str(corp_id)]['name'] = esi_result['corporation_name']
            corp_dict['corps'][str(corp_id)]['members'] = esi_result['member_count']
            corp_dict['corps'][str(corp_id)]['tokens'] = 0
            corp_dict['corps'][str(corp_id)]['registered'] = 0

        corp_dict['corps'][str(corp_id)]['registered'] += 1

        if 'esiAccessToken' in result:
            corp_dict['corps'][str(corp_id)]['tokens'] += 1

    js = json.dumps(corp_dict)
    return Response(js, status=200, mimetype='application/json')

        







