from flask import request
from tri_api import app

@app.route('/core/trisupers/', methods=[ 'GET' ])
def core_trisupers():
    from flask import request, Response
    from concurrent.futures import ThreadPoolExecutor, as_completed
    from common.check_role import check_role
    import common.ldaphelpers as _ldaphelpers
    import common.logger as _logger
    import json

    ipaddress = request.headers['X-Real-Ip']


    try:
        charid = int(request.args.get('charid'))
    except ValueError:
        _logger.log('[' + __name__ + '] charid parameters must be integer: {0}'.format(request.args.get('charid')),
                    _logger.LogLevel.WARNING)
        js = json.dumps({'error': 'charid parameter must be integer'})
        resp = Response(js, status=401, mimetype='application/json')
        return resp

    _logger.securitylog(__name__, 'corp audit information request', ipaddress=ipaddress, charid=charid)

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

    # get super pilots

    filterstr = '(&(esiAccessToken=*)(alliance=933731581))'
    attrlist = ['uid', 'corporation', 'characterName', 'altOf']

    code_supers, result_supers = _ldaphelpers.ldap_search(__name__, dn, filterstr, attrlist)

    supers = dict()

    with ThreadPoolExecutor(30) as executor:
        futures = { executor.submit(audit_pilot, result_supers[cn]): cn for cn in result_supers }
        for future in as_completed(futures):
            data = future.result()

            try:
                supers.update(data)
            except Exception as err:
                _logger.log('[' + __name__ + '] super audit for failed: {0}'.format(err), _logger.LogLevel.ERROR)

    js = json.dumps(supers)
    return Response(js, status=200, mimetype='application/json')


@app.route('/core/corpsupers/', methods=['GET'])
def core_corpsupers():
    from flask import request, Response
    from concurrent.futures import ThreadPoolExecutor, as_completed
    from common.check_role import check_role
    import common.ldaphelpers as _ldaphelpers
    import common.logger as _logger
    import common.request_esi
    import json

    ipaddress = request.headers['X-Real-Ip']


    try:
        charid = int(request.args.get('charid'))
    except ValueError:
        _logger.log('[' + __name__ + '] charid parameters must be integer: {0}'.format(request.args.get('charid')),
                    _logger.LogLevel.WARNING)
        js = json.dumps({'error': 'charid parameter must be integer'})
        resp = Response(js, status=401, mimetype='application/json')
        return resp

    _logger.securitylog(__name__, 'corp audit information request', ipaddress=ipaddress, charid=charid)

    # check for auth groups

    corporation_id_list = []
    character_id_list = []

    dn = 'ou=People,dc=triumvirate,dc=rocks'
    code, char_result = _ldaphelpers.ldap_search(__name__, dn, '(&(|(uid={0})(altOf={0}))(esiAccessToken=*))'
                                                 .format(charid), ['uid', 'corporation'])

    if code == False:
        error = 'failed to fetch characters for {0}: ({1}) {2}'.format(charid, code, char_result)
        _logger.log('[' + __name__ + ']' + error, _logger.LogLevel.ERROR)
        js = json.dumps({'error': error})
        resp = Response(js, status=500, mimetype='application/json')
        return resp

    for cn in char_result:
        data = char_result[cn]
        allowed_roles = ['Director', 'Personnel_Manager']
        code, result = check_role(__name__, data['uid'], allowed_roles)

        if code == 'error':
            error = 'unable to check character roles for {0}: ({1}) {2}'.format(data['uid'], code, result)
            _logger.log('[' + __name__ + ']' + error, _logger.LogLevel.ERROR)
            js = json.dumps({'error': error})
            resp = Response(js, status=500, mimetype='application/json')
            return resp
        elif code == False:
            pass
        else:
            _logger.log('[' + __name__ + '] sufficient roles to view corp auditing information', _logger.LogLevel.DEBUG)

            if data['corporation'] not in corporation_id_list:
                request_url = 'corporations/{0}/members/?datasource=tranquility'.format(data['corporation'])
                code, result = common.request_esi.esi(__name__, request_url, method='get', charid=data['uid'],
                                                      version='v2')

                if not code == 200:
                    # something broke severely
                    _logger.log('[' + __name__ + '] corporations API error {0}: {1}'.format(code, result['error']),
                                _logger.LogLevel.ERROR)
                    error = result['error']
                    result = {'code': code, 'error': error}
                    return code, result

                character_id_list += [char['character_id'] for char in result]
                corporation_id_list.append(data['corporation'])

    supers = dict()

    with ThreadPoolExecutor(30) as executor:
        futures = { executor.submit(audit_pilot_byid, user): user for user in character_id_list }
        for future in as_completed(futures):
            data = future.result()

            try:
                supers.update(data)
            except Exception as err:
                _logger.log('[' + __name__ + '] super audit for failed: {0}'.format(err), _logger.LogLevel.ERROR)

    js = json.dumps(supers)
    return Response(js, status=200, mimetype='application/json')


def audit_pilot(entry):
    from flask import request, Response
    from concurrent.futures import ThreadPoolExecutor, as_completed
    from common.check_role import check_role
    import common.ldaphelpers as _ldaphelpers
    import common.esihelpers as _esihelpers
    import common.logger as _logger
    import common.check_scope as _check_scope
    import common.request_esi
    import json

    ships = dict()
    basic_pilot = dict()

    uid = entry['uid']

    _logger.log('[' + __name__ + '] auditing character ' + uid, _logger.LogLevel.DEBUG)

    corpid = entry['corporation']
    charname = entry['characterName']
    altOf = entry['altOf']
    corpid = entry['corporation']

    # data pollution fix
    if altOf == 'None': altOf = None

    basic_pilot['uid'] = uid
    basic_pilot['pilot'] = charname
    basic_pilot['valid'] = False
    basic_pilot['main_charid'] = altOf

    corp_info = _esihelpers.corporation_info(corpid)

    if corp_info is not None:
        basic_pilot['corporation'] = corp_info['corporation_name']
    else:
        basic_pilot['corporation'] = "Unknown"

    # hardcoded data for asset typeids
    titans = {
        11567: 'Avatar',
        671: 'Erebus',
        45649: 'Komodo',
        3764: 'Leviathan',
        42241: 'Molok',
        23773: 'Ragnarok',
    }
    supers = {
        23919: 'Aeon',
        22852: 'Hel',
        23913: 'Nyx',
        3514: 'Revenant',
        42125: 'Vendetta',
        23917: 'Wyvern'
    }


    # fetch current ship

    code, current_ship = _esihelpers.current_ship(uid)

    if code == False:
        return ships

    # fetch super/titan typeids out of char assets

    code, char_assets = _esihelpers.find_types(uid, list(titans) + list(supers))
    if code == False:
        return ships

    # fetch character location

    code, location = _esihelpers.char_location(uid)
    if code == False:
        return ships

    # fetch main charname, if it exists

    dn = 'ou=People,dc=triumvirate,dc=rocks'
    filterstr = 'uid={}'.format(altOf)
    attrlist = ['uid', 'characterName']

    if not altOf == None:
        result = _ldaphelpers.ldap_uid2name(__name__, altOf)
        if result == None:
            msg = 'failed to find main for {0}'.format(altOf)
            _logger.log('[' + __name__ + ']' + msg, _logger.LogLevel.WARNING)
        try:
            main = result['characterName']
        except:
            main = "Unknown"
    else:
        main = charname

    # does this character have a titan/super in assets?

    for asset in char_assets:
        asset_typeid = asset.get('type_id')
        asset_id = asset.get('item_id')
        if asset_typeid in list(titans) + list(supers):
            ships[asset_id] = basic_pilot
            ships[asset_id]['typeid'] = asset_typeid
            ships[asset_id]['main_charname'] = main
            ships[asset_id]['active'] = False
            ships[asset_id]['location_id'] = asset['location_id']
            ships[asset_id]['location_name'] = 'Unkown'

        if asset_typeid in list(supers):
            ships[asset_id]['type'] = supers[asset_typeid]
            ships[asset_id]['class'] = "Supercarrier"
        if asset_typeid in list(titans):
            ships[asset_id]['type'] = titans[asset_typeid]
            ships[asset_id]['class'] = "Titan"

    # is this character flying a titan/super?
    # this is last to override the asset search with the active super (if any)

    active_typeid = current_ship.get('ship_type_id')
    active_id = current_ship.get('ship_item_id')

    if active_typeid in list(titans) + list(supers):
        # setup basics
        ships[active_id] = basic_pilot
        ships[active_id]['typeid'] = active_typeid
        ships[active_id]['main_charname'] = main
        ships[active_id]['active'] = True
        ships[active_id]['location_name'] = location['location']
        # more complex location ids and names can be filled in later?

    # actual ship specific shit
    if active_typeid in list(titans):
        ships[active_id]['type'] = titans[active_typeid]
        ships[active_id]['class'] = "Titan"

    if active_typeid in list(supers):
        ships[active_id]['type'] = supers[active_typeid]
        ships[active_id]['class'] = "Supercarrier"

    return ships

def audit_pilot_byid(char_id):
    from flask import request, Response
    from concurrent.futures import ThreadPoolExecutor, as_completed
    from common.check_role import check_role
    import common.ldaphelpers as _ldaphelpers
    import common.esihelpers as _esihelpers
    import common.logger as _logger
    import common.check_scope as _check_scope
    import common.request_esi
    import json

    ships = dict()
    basic_pilot = dict()

    uid = char_id

    char_info = _esihelpers.character_info(char_id)

    if char_info is None:
        return None

    _logger.log('[' + __name__ + '] auditing character ' + uid, _logger.LogLevel.DEBUG)

    corpid = char_info['corporation_id']
    charname = char_info['name']

    # get altOf
    dn = 'ou=People,dc=triumvirate,dc=rocks'
    code, char_result = _ldaphelpers.ldap_search(__name__, dn, '(&(uid={0})(esiAccessToken=*))'
                                                 .format(char_id), ['altOf'])

    if not code:
        error = 'failed to fetch characters for {0}: ({1}) {2}'.format(char_id, code, char_result)
        _logger.log('[' + __name__ + ']' + error, _logger.LogLevel.ERROR)
        js = json.dumps({'error': error})
        resp = Response(js, status=500, mimetype='application/json')
        return resp

    altOf = char_result['altOf']

    # data pollution fix
    if altOf == 'None': altOf = None

    basic_pilot['uid'] = uid
    basic_pilot['pilot'] = charname
    basic_pilot['valid'] = False
    basic_pilot['main_charid'] = altOf

    corp_info = _esihelpers.corporation_info(corpid)

    if corp_info is not None:
        basic_pilot['corporation'] = corp_info['corporation_name']
    else:
        basic_pilot['corporation'] = "Unknown"

    # hardcoded data for asset typeids
    titans = {
        11567: 'Avatar',
        671: 'Erebus',
        45649: 'Komodo',
        3764: 'Leviathan',
        42241: 'Molok',
        23773: 'Ragnarok',
    }
    supers = {
        23919: 'Aeon',
        22852: 'Hel',
        23913: 'Nyx',
        3514: 'Revenant',
        42125: 'Vendetta',
        23917: 'Wyvern'
    }


    # fetch current ship

    code, current_ship = _esihelpers.current_ship(uid)

    if code == False:
        return ships

    # fetch super/titan typeids out of char assets

    code, char_assets = _esihelpers.find_types(uid, list(titans) + list(supers))
    if code == False:
        return ships

    # fetch character location

    code, location = _esihelpers.char_location(uid)
    if code == False:
        return ships

    # fetch main charname, if it exists

    dn = 'ou=People,dc=triumvirate,dc=rocks'
    filterstr = 'uid={}'.format(altOf)
    attrlist = ['uid', 'characterName']

    if not altOf == None:
        result = _ldaphelpers.ldap_uid2name(__name__, altOf)
        if result == None:
            msg = 'failed to find main for {0}'.format(altOf)
            _logger.log('[' + __name__ + ']' + msg, _logger.LogLevel.WARNING)
        try:
            main = result['characterName']
        except:
            main = "Unknown"
    else:
        main = charname

    # does this character have a titan/super in assets?

    for asset in char_assets:
        asset_typeid = asset.get('type_id')
        asset_id = asset.get('item_id')
        if asset_typeid in list(titans) + list(supers):
            ships[asset_id] = basic_pilot
            ships[asset_id]['typeid'] = asset_typeid
            ships[asset_id]['main_charname'] = main
            ships[asset_id]['active'] = False
            ships[asset_id]['location_id'] = asset['location_id']
            ships[asset_id]['location_name'] = 'Unkown'

        if asset_typeid in list(supers):
            ships[asset_id]['type'] = supers[asset_typeid]
            ships[asset_id]['class'] = "Supercarrier"
        if asset_typeid in list(titans):
            ships[asset_id]['type'] = titans[asset_typeid]
            ships[asset_id]['class'] = "Titan"

    # is this character flying a titan/super?
    # this is last to override the asset search with the active super (if any)

    active_typeid = current_ship.get('ship_type_id')
    active_id = current_ship.get('ship_item_id')

    if active_typeid in list(titans) + list(supers):
        # setup basics
        ships[active_id] = basic_pilot
        ships[active_id]['typeid'] = active_typeid
        ships[active_id]['main_charname'] = main
        ships[active_id]['active'] = True
        ships[active_id]['location_name'] = location['location']
        # more complex location ids and names can be filled in later?

    # actual ship specific shit
    if active_typeid in list(titans):
        ships[active_id]['type'] = titans[active_typeid]
        ships[active_id]['class'] = "Titan"

    if active_typeid in list(supers):
        ships[active_id]['type'] = supers[active_typeid]
        ships[active_id]['class'] = "Supercarrier"

    return ships

