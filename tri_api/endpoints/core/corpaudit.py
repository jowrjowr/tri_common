from flask import request
from tri_api import app

@app.route('/core/corpaudit/<charid>', methods=[ 'GET' ])
def core_corpaudit(charid):

    from flask import request, Response
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
        _logger.log('[' + __name__ + '] charid parameters must be integer: {0}'.format(charid), _logger.LogLevel.WARNING)
        js = json.dumps({ 'error': 'charid parameter must be integer'})
        resp = Response(js, status=401, mimetype='application/json')
        return resp

    # check for roles

    allowed_roles = ['Director', 'Personnel_Manager']
    code, result = check_role(__name__, charid, allowed_roles)

    if code == 'error':
        error = 'unable to check character roles for {0}: ({1}) {2}'.format(charid, code, result)
        _logger.log('[' + __name__ + ']' + error,_logger.LogLevel.ERROR)
        js = json.dumps({ 'error': error})
        resp = Response(js, status=500, mimetype='application/json')
        return resp
    elif code == False:
        error = 'insufficient corporate roles to access this endpoint.'
        _logger.log('[' + __name__ + '] ' + error,_logger.LogLevel.INFO)
        js = json.dumps({ 'error': error})
        resp = Response(js, status=403, mimetype='application/json')
        return resp
    else:
        _logger.log('[' + __name__ + '] sufficient roles to view corp auditing information',_logger.LogLevel.DEBUG)

    # get character affiliations to determine corp (could use ldap)
    request_url = 'characters/affiliation/?datasource=tranquility'
    data = '[{}]'.format(charid)
    code, result = common.request_esi.esi(__name__, request_url, method='post', data=data)

    if not code == 200:
        # something broke severely
        _logger.log('[' + __name__ + '] affiliations API error {0}: {1}'.format(code, result['error']),
            _logger.LogLevel.ERROR)
        error = result['error']
        result = {'code': code, 'error': error}
        return code, result

    corpid = result[0]['corporation_id']
    # get list of corp members

    request_url = 'corporations/{0}/members/?datasource=tranquility'.format(corpid)
    code, result = common.request_esi.esi(__name__, request_url, method='get', charid=charid, version='v2')

    if not code == 200:
        # something broke severely
        _logger.log('[' + __name__ + '] corporations API error {0}: {1}'.format(code, result['error']),
            _logger.LogLevel.ERROR)
        error = result['error']
        result = {'code': code, 'error': error}
        return code, result

    # start constructing which member has what

    users = dict()

    for user in result:
        charid = user['character_id']
        users[charid] = dict()

        dn = 'ou=People,dc=triumvirate,dc=rocks'
        filterstr='(uid={})'.format(charid)
        attrlist=['characterName', 'authGroup', 'teamspeakdbid', 'esiAccessToken', 'altOf' ]
        code, result = _ldaphelpers.ldap_search(__name__, dn, filterstr, attrlist)

        if code == False:
            msg = 'unable to fetch ldap information: {}'.format(error)
            _logger.log('[' + __name__ + '] {}'.format(msg),_logger.LogLevel.ERROR)
            js = json.dumps({ 'error': msg })
            return Response(js, status=500, mimetype='application/json')

        if result == None:
            # no result? simple response.
            users[charid]['location'] = 'Unknown'
            users[charid]['online'] = 'Unknown'
            users[charid]['last_online'] = 'Unknown'
            users[charid]['token_status'] = False
            users[charid]['teamspeak_status'] = False
            users[charid]['isalt'] = 'Unknown'
            users[charid]['altof'] = None

            # map the id to a name

            request_url = 'characters/{0}/?datasource=tranquility'.format(charid)
            code, result = common.request_esi.esi(__name__, request_url, 'get')

            if not code == 200:
                _logger.log('[' + function + '] /characters API error {0}: {1}'.format(code, result['error']), _logger.LogLevel.ERROR)
                charname = 'Unknown'
            try:
                charname = result['name']
            except KeyError as error:
                _logger.log('[' + function + '] User does not exist: {0})'.format(charid), _logger.LogLevel.ERROR)
                charname = None

            users[charid]['charname'] = charname

            continue

        else:
            (dn, info), = result.items()

            users[charid]['charname'] = info['characterName']

            # does the char have a token?

            try:
                detail = info['esiAccessToken']
                if len(detail) > 0:
                    users[charid]['token_status'] = True
                else:
                    users[charid]['token_status'] = False
            except Exception as e:
                users[charid]['token_status'] = False

            # teamspeak registration?
            try:
                detail = info['teamspeakdbid']
                if len(detail) > 0:
                    users[charid]['teamspeak_status'] = True
                else:
                    users[charid]['teamspeak_status'] = False
            except Exception as e:
                users[charid]['teamspeak_status'] = False

            # is this an alt?

            # cast the altof detail to something useful

            try:
                detail = info['altOf']
            except Exception as e:
                detail = None

            # str(None) == False
            if str(detail).isdigit():
                users[charid]['isalt'] = True
                request_url = 'characters/{0}/?datasource=tranquility'.format(detail)
                code, result = common.request_esi.esi(__name__, request_url, 'get')

                if not code == 200:
                    _logger.log('[' + function + '] /characters API error {0}: {1}'.format(code, result['error']), _logger.LogLevel.WARNING)
                try:
                    users[charid]['altof'] = result['name']
                except KeyError as error:
                    _logger.log('[' + function + '] User does not exist: {0})'.format(charid), _logger.LogLevel.ERROR)
                    users[charid]['altof'] = 'Unknown'
            else:
                users[charid]['altof'] = None
                users[charid]['isalt'] = False

            ## start fetching character-specific information

            #
            request_url = 'characters/{0}/location/?datasource=tranquility'.format(charid)
            code, result = common.request_esi.esi(__name__, request_url, method='get', charid=charid, version='v1')

            if not code == 200:
                # it doesn't really matter
                _logger.log('[' + __name__ + '] characters loction API error {0}: {1}'.format(code, result['error']),_logger.LogLevel.DEBUG)
                location = None
                users[charid]['location_id'] = location
                users[charid]['location'] = 'Unknown'
            else:
                # can include either station_id or structure_id
                location = result['solar_system_id']
                users[charid]['location_id'] = location

            request_url = 'characters/{0}/location/?datasource=tranquility'.format(charid)
            code, result = common.request_esi.esi(__name__, request_url, method='get', charid=charid, version='v1')

            if not code == 200:
                # it doesn't really matter
                _logger.log('[' + __name__ + '] characters loction API error {0}: {1}'.format(code, result['error']),_logger.LogLevel.DEBUG)
                location = None
            else:
                # can include either station_id or structure_id
                location = result['solar_system_id']

            users[charid]['location_id'] = location

            # map the location to a name
            if location == None:
                users[charid]['location'] = 'Unknown'
            else:
                request_url = 'universe/systems/{0}/'.format(location)
                code, result = common.request_esi.esi(__name__, request_url, 'get')
                if not code == 200:
                    _logger.log('[' + __name__ + '] /universe/systems API error ' + str(code) + ': ' + str(data['error']), _logger.LogLevel.INFO)
                    users[charid]['location'] = 'Unknown'
                else:
                    users[charid]['location'] = result['name']

            # get online status

            request_url = 'characters/{0}/online/?datasource=tranquility'.format(charid)
            code, result = common.request_esi.esi(__name__, request_url, method='get', charid=charid, version='v2')

            if not code == 200:
                # it doesn't really matter
                _logger.log('[' + __name__ + '] characters online API error {0}: {1}'.format(code, result['error']),_logger.LogLevel.DEBUG)
                location = None
                users[charid]['online'] = 'Unknown'
                users[charid]['last_online'] = 'Unknown'
            else:
                users[charid]['online'] = result['online']
                users[charid]['last_online'] = result['last_login']

    js = json.dumps(users)
    resp = Response(js, status=200, mimetype='application/json')
    return resp
