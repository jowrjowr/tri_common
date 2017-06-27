from flask import request
from tri_api import app

@app.route('/core/group/<group>/<charid>', methods=[ 'DELETE', 'POST' ])
def core_group_manage(group, charid):

    from flask import request
    import common.logger as _logger

    ipaddress = request.headers['X-Real-Ip']
    # remove the char from a group
    if request.method == 'DELETE':
        _logger.securitylog(__name__, 'removed charid {0} from group {1}'.format(charid, group), ipaddress=ipaddress)
        return group_DELETE(group, charid)

    # add the char to a group
    if request.method == 'POST':
        _logger.securitylog(__name__, 'added charid {0} to group {1}'.format(charid, group), ipaddress=ipaddress)
        return group_ADD(group, charid)

def group_DELETE(group, charid):

    import json
    import ldap
    import ldap.modlist
    import common.logger as _logger
    import common.credentials.ldap as _ldap
    import common.ldaphelpers as _ldaphelpers
    from flask import Response, request

    # initialize connections

    try:
        ldap_conn = ldap.initialize(_ldap.ldap_host, bytes_mode=False)
        ldap_conn.simple_bind_s(_ldap.admin_dn, _ldap.admin_dn_password)
    except ldap.LDAPError as error:
        msg = 'LDAP connection error: {}'.format(error)
        _logger.log('[' + __name__ + '] {}'.format(msg),_logger.LogLevel.ERROR)
        js = json.dumps({ 'error': msg })
        return Response(js, status=500, mimetype='application/json')

    # find the user. partly to get the dn, partly to validate.

    dn = 'ou=People,dc=triumvirate,dc=rocks'
    filterstr='(uid={})'.format(charid)
    attrlist=['characterName', 'authGroup' ]
    code, result = _ldaphelpers.ldap_search(__name__, dn, filterstr, attrlist)

    if code == False:
        msg = 'unable to fetch ldap information: {}'.format(error)
        _logger.log('[' + __name__ + '] {}'.format(msg),_logger.LogLevel.ERROR)
        js = json.dumps({ 'error': msg })
        return Response(js, status=500, mimetype='application/json')


    if result == None:
        msg = 'charid {0} not in ldap'.format(charid)
        _logger.log('[' + __name__ + '] {}'.format(msg),_logger.LogLevel.ERROR)
        js = json.dumps({ 'error': msg })
        return Response(js, status=404, mimetype='application/json')


    (dn, info), = result.items()

    # modify the user

    group = group.encode('utf-8')
    mod_attrs = [ (ldap.MOD_DELETE, 'authGroup', group) ]

    try:
        ldap_conn.modify_s(dn, mod_attrs)
    except ldap.LDAPError as error:
        msg = 'unable to modify {0}: {1}'.format(dn, error)
        _logger.log('[' + __name__ + '] {}'.format(msg),_logger.LogLevel.ERROR)
        js = json.dumps({ 'error': msg })
        return Response(js, status=500, mimetype='application/json')

    return Response({}, status=200, mimetype='application/json')

def group_ADD(group, charid):

    import json
    import ldap
    import ldap.modlist
    import common.logger as _logger
    import common.credentials.ldap as _ldap
    import common.ldaphelpers as _ldaphelpers
    from flask import Response, request

    # initialize connections

    try:
        ldap_conn = ldap.initialize(_ldap.ldap_host, bytes_mode=False)
        ldap_conn.simple_bind_s(_ldap.admin_dn, _ldap.admin_dn_password)
    except ldap.LDAPError as error:
        msg = 'LDAP connection error: {}'.format(error)
        _logger.log('[' + __name__ + '] {}'.format(msg),_logger.LogLevel.ERROR)
        js = json.dumps({ 'error': msg })
        return Response(js, status=500, mimetype='application/json')

    # find the user. partly to get the dn, partly to validate.

    dn = 'ou=People,dc=triumvirate,dc=rocks'
    filterstr='(uid={})'.format(charid)
    attrlist=['characterName', 'authGroup' ]
    code, result = _ldaphelpers.ldap_search(__name__, dn, filterstr, attrlist)

    if code == False:
        msg = 'unable to fetch ldap information: {}'.format(error)
        _logger.log('[' + __name__ + '] {}'.format(msg),_logger.LogLevel.ERROR)
        js = json.dumps({ 'error': msg })
        return Response(js, status=500, mimetype='application/json')


    if result == None:
        msg = 'charid {0} not in ldap'.format(charid)
        _logger.log('[' + __name__ + '] {}'.format(msg),_logger.LogLevel.ERROR)
        js = json.dumps({ 'error': msg })
        return Response(js, status=404, mimetype='application/json')


    (dn, info), = result.items()

    # modify the user

    group = group.encode('utf-8')
    mod_attrs = [ (ldap.MOD_ADD, 'authGroup', group) ]

    try:
        ldap_conn.modify_s(dn, mod_attrs)
    except ldap.LDAPError as error:
        msg = 'unable to modify {0}: {1}'.format(dn, error)
        _logger.log('[' + __name__ + '] {}'.format(msg),_logger.LogLevel.ERROR)
        js = json.dumps({ 'error': msg })
        return Response(js, status=500, mimetype='application/json')

    return Response({}, status=200, mimetype='application/json')


@app.route('/core/group/<group>', methods=[ 'GET' ])
def core_group_members(group):

    import json
    import common.logger as _logger
    import common.ldaphelpers as _ldaphelpers
    import common.request_esi
    from common.api import base_url
    from flask import Response, request

    # get the list of group members for this group

    ipaddress = request.headers['X-Real-Ip']

    # snag groups

    dn = 'ou=People,dc=triumvirate,dc=rocks'
    filterstr='(authGroup={})'.format(group)
    attrlist=['characterName', 'authGroup', 'uid', 'corporation', 'alliance', 'teamspeakdbid', 'esiAccessToken' ]
    code, result = _ldaphelpers.ldap_search(__name__, dn, filterstr, attrlist)

    if code == False:
        msg = 'unable to fetch ldap information: {}'.format(error)
        _logger.log('[' + __name__ + '] {}'.format(msg),_logger.LogLevel.ERROR)
        js = json.dumps({ 'error': msg })
        return Response(js, status=500, mimetype='application/json')


    if result == None:
        msg = 'charid {0} not in ldap'.format(charid)
        _logger.log('[' + __name__ + '] {}'.format(msg),_logger.LogLevel.ERROR)
        js = json.dumps({ 'error': msg })
        return Response(js, status=404, mimetype='application/json')

    # construct the response object

    response = dict()
    response['count'] = len(result)
    response['users'] = []

    for user in result.keys():

        details = result[user]

        info = dict()
        info['uid'] = int( details['uid'] )
        info['charname'] = details['characterName']

        # alliance name
        allianceid = int( details['alliance'] )
        info['allianceid'] = allianceid

        request_url = base_url + "alliances/" + str(allianceid) + '/?datasource=tranquility'

        code, esi_result = common.request_esi.esi(__name__, request_url, 'get')

        if not code == 200:
            _logger.log('[' + __name__ + '] /alliances API error {0}: {1}'.format(code, esi_result['error']), _logger.LogLevel.ERROR)
            info['alliance_name'] = 'Unknown'
        else:
            info['alliance_name'] = esi_result['alliance_name']

        # corp name

        corpid = int( details['corporation'] )
        info['corpid'] = corpid
        request_url = base_url + 'corporations/{0}/?datasource=tranquility'.format(corpid)
        code, esi_result = common.request_esi.esi(__name__, request_url, 'get')

        if code != 200:
            _logger.log('[' + __name__ + '] corporations API error {0}: {1}'.format(code, esi_result['error']),_logger.LogLevel.ERROR)
            info['corp_name'] = 'Unknown'
        else:
            info['corp_name'] = esi_result['corporation_name']

        # ESI token status
        token = details['esiAccessToken']
        if token == None:
            info['esi_token'] = False
        else:
            info['esi_token'] = True

        # comms status
        teamspeak = details['teamspeakdbid']
        if teamspeak == None:
            info['teamspeak'] = False
        else:
            info['teamspeak'] = True

        response['users'].append(info)

    js = json.dumps(response)
    return Response(js, status=200, mimetype='application/json')

@app.route('/core/chargroups/<charid>', methods=[ 'GET' ])
def core_chargroups(charid):

    import json
    import common.logger as _logger
    import common.ldaphelpers as _ldaphelpers
    from flask import Response, request

    # get the list of groups for this charid
    ipaddress = request.headers['X-Real-Ip']

    try:
        charid = int(charid)
    except ValueError:
        _logger.log('[' + __name__ + '] invalid charid: "{0}"'.format(charid), _logger.LogLevel.WARNING)
        js = json.dumps({ 'error': 'charid parameter must be integer'})
        return Response(js, status=401, mimetype='application/json')

    # snag groups

    dn = 'ou=People,dc=triumvirate,dc=rocks'
    filterstr='(uid={})'.format(charid)
    attrlist=['characterName', 'authGroup' ]
    code, result = _ldaphelpers.ldap_search(__name__, dn, filterstr, attrlist)

    if code == False:
        msg = 'unable to fetch ldap information: {}'.format(error)
        _logger.log('[' + __name__ + '] {}'.format(msg),_logger.LogLevel.ERROR)
        js = json.dumps({ 'error': msg })
        return Response(js, status=500, mimetype='application/json')


    if result == None:
        msg = 'charid {0} not in ldap'.format(charid)
        _logger.log('[' + __name__ + '] {}'.format(msg),_logger.LogLevel.ERROR)
        js = json.dumps({ 'error': msg })
        return Response(js, status=404, mimetype='application/json')


    (dn, info), = result.items()

    response = dict()
    response['groups'] = info['authGroup']

    js = json.dumps(response)
    return Response(js, status=200, mimetype='application/json')
