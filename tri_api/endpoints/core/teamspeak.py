from flask import request
from tri_api import app

@app.route('/core/teamspeak/<charid>', methods=['DELETE', 'GET', 'POST'])
def core_teamspeak(charid):

    from flask import request
    import common.logger as _logger

    ipaddress = request.headers['X-Real-Ip']
    # remove the TS information from a given char
    if request.method == 'DELETE':
        _logger.securitylog(__name__, 'teamspeak identity delete', charid=charid, ipaddress=ipaddress)
        return teamspeak_DELETE(charid)

    # get current TS info for a charid
    if request.method == 'GET':
        return teamspeak_GET(charid)

    # update/make new teamspeak identity
    if request.method == 'POST':
        _logger.securitylog(__name__, 'teamspeak identity creation', charid=charid, ipaddress=ipaddress)
        return teamspeak_POST(charid)

def teamspeak_POST(charid):
    import json
    import ldap
    import ldap.modlist
    import ts3
    import common.request_esi
    import common.logger as _logger
    import common.credentials.ldap as _ldap
    import common.credentials.ts3 as _ts3
    from flask import Response, request
    from common.api import base_url
    from tri_core.common.tsgroups import teamspeak_groups

    # make a new ts3 identity

    # initialize connections

    try:
        ldap_conn = ldap.initialize(_ldap.ldap_host, bytes_mode=False)
        ldap_conn.simple_bind_s(_ldap.admin_dn, _ldap.admin_dn_password)
    except ldap.LDAPError as error:
        msg = 'LDAP connection error: {}'.format(error)
        _logger.log('[' + __name__ + '] {}'.format(msg),_logger.LogLevel.ERROR)
        js = json.dumps({ 'error': msg})
        resp = Response(js, status=500, mimetype='application/json')
        return resp

    try:
        # Note, that the client will wait for the response and raise a
        # **TS3QueryError** if the error id of the response is not 0.
        ts3conn = ts3.query.TS3Connection(_ts3.TS_HOST)
        ts3conn.login(
            client_login_name=_ts3.TS_USER,
            client_login_password=_ts3.TS_PASSWORD
        )
    except ts3.query.TS3QueryError as err:
        msg = 'unable to connect to TS3: {0}'.format(err.resp.error["msg"])
        _logger.log('[' + __name__ + '] {}'.format(msg),_logger.LogLevel.ERROR)
        js = json.dumps({ 'error': msg })
        resp = Response(js, status=500, mimetype='application/json')
        return resp

    ts3conn.use(sid=_ts3.TS_SERVER_ID)

    # snag existing ts info. this will matter later.
    try:
        result = ldap_conn.search_s('ou=People,dc=triumvirate,dc=rocks',
            ldap.SCOPE_SUBTREE,
            filterstr='(uid={})'.format(charid),
            attrlist=['teamspeakuid', 'teamspeakdbid', 'characterName', 'authGroup' ]
        )
        result_count = result.__len__()
    except ldap.LDAPError as error:
        msg = 'unable to fetch ldap users: {}'.format(error)
        _logger.log('[' + __name__ + '] {}'.format(msg),_logger.LogLevel.ERROR)
        js = json.dumps({ 'error': msg})
        resp = Response(js, status=500, mimetype='application/json')
        return resp

    if result_count == 0:
        # this should NEVER happen
        msg = 'charid {0} not in ldap'.format(error)
        _logger.log('[' + __name__ + '] {}'.format(msg),_logger.LogLevel.ERROR)
        js = json.dumps({ 'error': msg})
        resp = Response(js, status=404, mimetype='application/json')
        return resp

    dn, result = result[0]
    encodedgroups = result['authGroup']
    groups = []
    for group in encodedgroups:
        groups.append(group.decode('utf-8'))

    charname = result['characterName'][0].decode('utf-8')

    # get character affiliations

    request_url = base_url + 'characters/affiliation/?datasource=tranquility'
    data = '[{}]'.format(charid)
    code, result = common.request_esi.esi(__name__, request_url, method='post', data=data)

    if not code == 200:
        # something broke severely
        msg = 'affiliations API error {0}: {1}'.format(code, result['error'])
        _logger.log('[' + __name__ + '] {}'.format(msg),_logger.LogLevel.ERROR)
        js = json.dumps({ 'error': msg})
        resp = Response(js, status=500, mimetype='application/json')
        return resp

    corpid = result[0]['corporation_id']
    try:
        allianceid = result[0]['alliance_id']
    except KeyError:
        allianceid = 0

    # check if a duplicate
    try:
        ts_dbid = result['teamspeakdbid'][0].decode('utf-8')
        ts_uid = result['teamspeakuid'][0].decode('utf-8')
    except Exception as error:
        ts_dbid = None
        ts_uid = None

    if ts_dbid != None or ts_dbid != None:
        # we have a live account. nuke it and try again.
        msg = 'existing teamspeak client. dbid: {0} uid: {1}'.format(ts_dbid, ts_uid)
        _logger.log('[' + __name__ + '] {}'.format(msg),_logger.LogLevel.WARNING)
        js = json.dumps({ 'error': msg})
        resp = Response(js, status=400, mimetype='application/json')
        return resp

    # snag the client list

    try:
        resp = ts3conn.clientlist()
        clients = resp.parsed
    except ts3.query.TS3QueryError as err:
        msg = 'ts3 error: "{0}"'.format(err)
        _logger.log('[' + __name__ + '] {}'.format(msg),_logger.LogLevel.ERROR)
        js = json.dumps({ 'error': msg})
        resp = Response(js, status=500, mimetype='application/json')
        return resp

    # loop through the client list to find the matching client

    for client in clients:
        clid = client['clid']
        cldbid = client['client_database_id']
        client_username = client['client_nickname']

        if client_username == charname:
            # found a match.
            ts_dbid = client['client_database_id']
            ts_uid = client['clid']

    if ts_dbid == None or ts_uid == None:

        msg = 'unable to locate matching teamspeak user for {}'.format(charname)
        _logger.log('[' + __name__ + '] {}'.format(msg),_logger.LogLevel.ERROR)
        js = json.dumps({ 'error': msg})
        resp = Response(js, status=404, mimetype='application/json')
        return resp

    # we want the unique identifier
    try:
        resp = ts3conn.clientinfo(clid=ts_uid)
        result = resp.parsed
    except ts3.query.TS3QueryError as err:
        msg = 'ts3 error: "{0}"'.format(err)
        _logger.log('[' + __name__ + '] {}'.format(msg),_logger.LogLevel.ERROR)
        js = json.dumps({ 'error': msg})
        resp = Response(js, status=500, mimetype='application/json')
        return resp

    ts_uid = result[0]['client_unique_identifier']
    # matching account found. store in ldap.

    attrs = []
    attrs.append((ldap.MOD_REPLACE, 'teamspeakuid', ts_uid.encode('utf-8')))
    attrs.append((ldap.MOD_REPLACE, 'teamspeakdbid', ts_dbid.encode('utf-8')))

    try:
        result = ldap_conn.modify_s(dn, attrs)
    except ldap.LDAPError as error:
        msg = 'unable to update tokens for {0}: {1}'.format(charname,error)
        _logger.log('[' + __name__ + '] {}'.format(msg),_logger.LogLevel.ERROR)
        js = json.dumps({ 'error': msg})
        resp = Response(js, status=500, mimetype='application/json')
        return resp

    # setup groups for the ts user

    code, result = teamspeak_groups(charid)

    if code == False:
        msg = 'unable to setup teamspeak groups for {0}: {1}'.format(charname, result)
        _logger.log('[' + __name__ + '] {}'.format(msg),_logger.LogLevel.ERROR)
        js = json.dumps({ 'error': msg})
        return Response(js, status=500, mimetype='application/json')
    else:
        return Response({}, status=200, mimetype='application/json')

def teamspeak_GET(charid):
    import json
    import ldap
    import ldap.modlist
    import common.logger as _logger
    import common.credentials.ldap as _ldap
    from flask import Response, request

    # fetch the teamspeak information from a given charid
    try:
        ldap_conn = ldap.initialize(_ldap.ldap_host, bytes_mode=False)
        ldap_conn.simple_bind_s(_ldap.admin_dn, _ldap.admin_dn_password)
    except ldap.LDAPError as error:
        msg = 'LDAP connection error: {}'.format(error)
        _logger.log('[' + __name__ + '] {}'.format(msg),_logger.LogLevel.ERROR)
        js = json.dumps({ 'error': msg})
        resp = Response(js, status=500, mimetype='application/json')
        return resp

    try:
        result = ldap_conn.search_s('ou=People,dc=triumvirate,dc=rocks',
            ldap.SCOPE_SUBTREE,
            filterstr='(uid={})'.format(charid),
            attrlist=['teamspeakuid', 'teamspeakdbid' ]
        )
        result_count = result.__len__()
    except ldap.LDAPError as error:
        msg = 'unable to fetch ldap users: {}'.format(error)
        _logger.log('[' + __name__ + '] {}'.format(msg),_logger.LogLevel.ERROR)
        js = json.dumps({ 'error': msg})
        resp = Response(js, status=500, mimetype='application/json')
        return resp

    dn, result = result[0]

    try:
        ts_dbid = result['teamspeakdbid'][0].decode('utf-8')
        ts_uid = result['teamspeakuid'][0].decode('utf-8')
    except Exception as error:
        ts_dbid = None
        ts_uid = None

    result = dict()
    result['teamspeakdbid'] = ts_dbid
    result['teamspeakuid'] = ts_uid

    js = json.dumps(result)
    resp = Response(js, status=200, mimetype='application/json')
    return resp

def teamspeak_DELETE(charid):

    import json
    import ldap
    import ldap.modlist
    import ts3
    import common.logger as _logger
    import common.credentials.ldap as _ldap
    import common.credentials.ts3 as _ts3
    from flask import Response, request

    # remove the teamspeak information the character's ldap

    # connections

    try:
        # Note, that the client will wait for the response and raise a
        # **TS3QueryError** if the error id of the response is not 0.
        ts3conn = ts3.query.TS3Connection(_ts3.TS_HOST)
        ts3conn.login(
            client_login_name=_ts3.TS_USER,
            client_login_password=_ts3.TS_PASSWORD
        )
    except ts3.query.TS3QueryError as err:
        msg = 'unable to connect to TS3: {0}'.format(err.resp.error["msg"])
        _logger.log('[' + __name__ + '] {}'.format(msg),_logger.LogLevel.ERROR)
        js = json.dumps({ 'error': msg})
        resp = Response(js, status=500, mimetype='application/json')
        return resp

    ts3conn.use(sid=_ts3.TS_SERVER_ID)

    try:
        ldap_conn = ldap.initialize(_ldap.ldap_host, bytes_mode=False)
        ldap_conn.simple_bind_s(_ldap.admin_dn, _ldap.admin_dn_password)
    except ldap.LDAPError as error:
        _logger.log('[' + __name__ + '] LDAP connection error: {}'.format(error),_logger.LogLevel.ERROR)
        js = json.dumps({ 'error': 'ldap connection error'})
        resp = Response(js, status=500, mimetype='application/json')
        return resp

    # find the ldap entry

    try:
        result = ldap_conn.search_s('ou=People,dc=triumvirate,dc=rocks',
            ldap.SCOPE_SUBTREE,
            filterstr='(uid={})'.format(charid),
            attrlist=[ 'characterName', 'teamspeakdbid' ]
        )
        result_count = result.__len__()
    except ldap.LDAPError as error:
        msg = 'unable to fetch ldap users: {}'.format(error)
        _logger.log('[' + __name__ + '] {}'.format(msg),_logger.LogLevel.ERROR)
        js = json.dumps({ 'error': msg})
        resp = Response(js, status=500, mimetype='application/json')
        return resp

    if result_count == 0:
        # this should NEVER happen
        msg = 'charid {0} not in ldap'.format(error)
        _logger.log('[' + __name__ + '] {}'.format(msg),_logger.LogLevel.ERROR)
        js = json.dumps({ 'error': msg})
        resp = Response(js, status=404, mimetype='application/json')
        return resp

    dn, result = result[0]

    try:
        ts_dbid = result['teamspeakdbid'][0].decode('utf-8')
    except Exception as error:
        ts_dbid = None

    if ts_dbid == None:
        # shouldn't happen!
        msg = 'character {0} has no teamspeak to purge'.format(charid)
        _logger.log('[' + __name__ + '] {}'.format(msg),_logger.LogLevel.WARNING)
        js = json.dumps({ 'error': msg })
        resp = Response(js, status=404, mimetype='application/json')
        return resp

    # purge from ts3


    # have to kick before purging, but to do that the client id (not the dbid) has to be located
    # snag the client list

    try:
        resp = ts3conn.clientlist()
        clients = resp.parsed
    except ts3.query.TS3QueryError as err:
        msg = 'ts3 error: "{0}"'.format(err)
        _logger.log('[' + __name__ + '] {}'.format(msg),_logger.LogLevel.ERROR)
        js = json.dumps({ 'error': msg})
        resp = Response(js, status=500, mimetype='application/json')
        return resp

    # loop through the client list to find the matching client

    ts_uid = None

    for client in clients:
        clid = client['clid']

        if ts_dbid == client['client_database_id']:
            # found a match.
            ts_uid = client['clid']

    if not ts_uid == None:
        try:
            reason = 'kicking to purge old TS identity, reregister now'
            resp = ts3conn.clientkick(reasonid=5, reasonmsg=reason, clid=ts_uid)
        except ts3.query.TS3QueryError as err:
            msg = 'unable to kick client dbid {0}, client id {1} from teamspeak'.format(ts_dbid, ts_uid, err)
            _logger.log('[' + __name__ + '] {}'.format(msg),_logger.LogLevel.ERROR)
            js = json.dumps({ 'error': msg})
            resp = Response(js, status=500, mimetype='application/json')
            return resp

    try:
        resp = ts3conn.clientdbdelete(cldbid=ts_dbid)
    except ts3.query.TS3QueryError as err:
        msg = 'unable to remove client dbid {0} for charid {1}: "{2}"'.format(ts_dbid, charid, err)
        _logger.log('[' + __name__ + '] {}'.format(msg),_logger.LogLevel.ERROR)
        js = json.dumps({ 'error': msg})
        resp = Response(js, status=500, mimetype='application/json')
        return resp

    # purge from ldap

    mod_attrs = []
    mod_attrs.append((ldap.MOD_DELETE, 'teamspeakuid', None ))
    mod_attrs.append((ldap.MOD_DELETE, 'teamspeakdbid', None ))

    try:
        result = ldap_conn.modify_s(dn, mod_attrs)
    except ldap.LDAPError as error:
        msg = 'unable to remove teamspeak entries for user {0}: {1}'.format(dn, error)
        _logger.log('[' + __name__ + '] {}'.format(msg),_logger.LogLevel.ERROR)
        js = json.dumps({ 'error': msg })
        resp = Response(js, status=500, mimetype='application/json')
        return resp


    # success if we made it this far

    resp = Response('{}', status=200, mimetype='application/json')
    return resp
