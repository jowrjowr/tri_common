from flask import request
from tri_api import app

@app.route('/core/audit/alliance/<allianceid>/', methods=[ 'GET' ])
def core_audit_alliance(allianceid):
    from flask import request, Response
    from concurrent.futures import ThreadPoolExecutor, as_completed
    from common.check_role import check_role
    import common.ldaphelpers as _ldaphelpers
    import common.logger as _logger
    import common.check_scope as _check_scope
    import common.request_esi
    import json

    ipaddress = request.headers['X-Real-Ip']
    log_charid = request.args.get('log_charid')

    _logger.securitylog(__name__, 'corp audit information request', ipaddress=ipaddress, charid=log_charid)

    try:
        charid = int(request.args.get('charid'))
    except ValueError:
        _logger.log('[' + __name__ + '] charid parameters must be integer: {0}'.format(request.args.get('charid')),
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
        _logger.log('[' + __name__ + ']' + error, _logger.LogLevel.ERROR)
        js = json.dumps({'error': error})
        resp = Response(js, status=500, mimetype='application/json')
        return resp

    if result == None:
        msg = 'charid {0} not in ldap'.format(charid)
        _logger.log('[' + __name__ + '] {}'.format(msg), _logger.LogLevel.ERROR)
        js = json.dumps({'error': msg})
        return Response(js, status=404, mimetype='application/json')

    (_, result), = result.items()

    if not "tsadmin" in result['authGroup']:
        error = 'insufficient corporate roles to access this endpoint.'
        _logger.log('[' + __name__ + '] ' + error, _logger.LogLevel.INFO)
        js = json.dumps({'error': error})
        resp = Response(js, status=403, mimetype='application/json')
        return resp

    # get alliance corporations
    request_url = 'alliances/{}/corporations/?datasource=tranquility'.format(allianceid)
    esi_corp_code, esi_corp_result = common.request_esi.esi(__name__, request_url, method='get')

    if not esi_corp_code == 200:
        # something broke severely
        _logger.log('[' + __name__ + '] corporation API error {0}: {1}'.format(esi_corp_code, esi_corp_result['error']),
                    _logger.LogLevel.ERROR)
        error = esi_corp_result['error']
        err_result = {'code': esi_corp_code, 'error': error}
        return esi_corp_code, err_result

    corps = dict()

    with ThreadPoolExecutor(10) as executor:
        futures = { executor.submit(audit_corp, charid, allianceid, corp_id): corp_id for corp_id in esi_corp_result }
        for future in as_completed(futures):
            data = future.result()
            corps[data['id']] = data

    js = json.dumps(corps)
    return Response(js, status=200, mimetype='application/json')

def audit_corp(charid, allianceid, corp_id):
    from flask import request, Response
    from concurrent.futures import ThreadPoolExecutor, as_completed
    from common.check_role import check_role
    import common.ldaphelpers as _ldaphelpers
    import common.logger as _logger
    import common.check_scope as _check_scope
    import common.request_esi
    import json

    dn = 'ou=People,dc=triumvirate,dc=rocks'

    corp_result = {}

    corp_result['id'] = corp_id

    request_url = 'corporations/{}/?datasource=tranquility'.format(corp_id)
    esi_corporation_code, esi_corporation_result = common.request_esi.esi(__name__, request_url, method='get')

    if not esi_corporation_code == 200:
        # something broke severely
        _logger.log('[' + __name__ + '] corporation API error {0}: {1}'.format(esi_corporation_code,
                                                                               esi_corporation_result['error']),
                    _logger.LogLevel.ERROR)
        error = esi_corporation_result['error']
        err_result = {'code': esi_corporation_code, 'error': error}
        return esi_corporation_code, err_result

    corp_result['name'] = esi_corporation_result['corporation_name']
    corp_result['members'] = esi_corporation_result['member_count']

    code_mains, result_mains = _ldaphelpers.ldap_search(__name__, dn,
                                                        '(&(corporation={0})((!(altOf=*)))'
                                                        .format(corp_id), [])

    if code_mains == 'error':
        error = 'unable to check auth groups roles for {0}: ({1}) {2}'.format(charid, code_mains, result_mains)
        _logger.log('[' + __name__ + ']' + error, _logger.LogLevel.ERROR)
        js = json.dumps({'error': error})
        resp = Response(js, status=500, mimetype='application/json')
        return resp
    code_registered, result_registered = _ldaphelpers.ldap_search(__name__, dn,
                                                                  '(corporation={0})'
                                                                  .format(corp_id), [])

    if code_registered == 'error':
        error = 'unable to check auth groups roles for {0}: ({1}) {2}'\
            .format(charid, code_registered, result_registered)
        _logger.log('[' + __name__ + ']' + error, _logger.LogLevel.ERROR)
        js = json.dumps({'error': error})
        resp = Response(js, status=500, mimetype='application/json')
        return resp

    code_tokens, result_tokens = _ldaphelpers.ldap_search(__name__, dn,
                                                        '(&(corporation={0})((esiAccessToken=*))'
                                                        .format(corp_id), [])

    if code_mains == 'error':
        error = 'unable to check auth groups roles for {0}: ({1}) {2}'.format(charid, code_tokens, result_tokens)
        _logger.log('[' + __name__ + ']' + error, _logger.LogLevel.ERROR)
        js = json.dumps({'error': error})
        resp = Response(js, status=500, mimetype='application/json')
        return resp

    corp_result['tokens'] = len(result_tokens)
    corp_result['registered'] = len(result_registered)
    corp_result['mains'] = len(result_mains)

    return corp_result
