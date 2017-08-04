from flask import request
from tri_api import app

@app.route('/core/trisupers/', methods=[ 'GET' ])
def core_trisupers():
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

    # get super pilots
    code_supers, result_supers = _ldaphelpers.ldap_search(__name__, dn, '(alliance=933731581)',
                                                          ['uid', 'corporation', 'characterName',
                                                           'esiAccessToken', 'altOf'])

    supers = dict()

    with ThreadPoolExecutor(10) as executor:
        futures = { executor.submit(audit_pilot, result_supers[cn]): cn for cn in result_supers }
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
    import common.logger as _logger
    import common.check_scope as _check_scope
    import common.request_esi
    import json

    ships = dict()
    basic_pilot = dict()

    uid = entry['uid']
    corpid = entry['corporation']
    charname = entry['characterName']
    token = entry['esiAccessToken']
    altOf = entry['altOf']

    basic_pilot['uid'] = uid
    basic_pilot['pilot'] = charname
    basic_pilot['valid'] = False

    # check if asset scope is available
    scope_code, _ = _check_scope.check_scope(__name__, uid,
                                             ['esi-location.read_location.v1',
                                              'esi-location.read_ship_type.v1'])

    if token is not None and scope_code:
        request_ship_url = 'characters/{}/ship/?datasource=tranquility'.format(uid)
        esi_ship_code, esi_ship_result = common.request_esi.esi(__name__, request_ship_url, method='get',
                                                                charid=uid)

        if esi_ship_code != 200:
            # something broke severely
            _logger.log('[' + __name__ + '] ship API error {0}: {1}'.format(esi_ship_code, esi_ship_result['error']),
                        _logger.LogLevel.ERROR)
            error = esi_ship_result['error']
            err_result = {'code': esi_ship_code, 'error': error}
            raise Exception(error)

        dn = 'ou=People,dc=triumvirate,dc=rocks'
        if altOf is not None and altOf != "None":
            main_code, main_result = _ldaphelpers.ldap_search(__name__, dn, 'uid={}'.format(altOf),
                                                              ['uid', 'characterName'])

            if main_code == 'error':
                error = 'failed to find main for {0}: ({1}) {2}'.format(altOf, main_code, main_result)
                _logger.log('[' + __name__ + ']' + error, _logger.LogLevel.ERROR)
                js = json.dumps({'error': error})
                resp = Response(js, status=500, mimetype='application/json')
                raise Exception(error)
            try:
                (_, main_result), = main_result.items()
                main = main_result['characterName']
            except:
                main = "Unkown"

        else:
            main = charname

        # check ship
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

        if esi_ship_result['ship_type_id'] in titans.keys():
            ships[esi_ship_result['ship_item_id']] = basic_pilot
            ships[esi_ship_result['ship_item_id']]['ship_type'] = titans[esi_ship_result['ship_type_id']]
            ships[esi_ship_result['ship_item_id']]['super_type'] = "Titan"
            ships[esi_ship_result['ship_item_id']]['main'] = main
            ships[esi_ship_result['ship_item_id']]['active'] = True

        elif esi_ship_result['ship_type_id'] in supers.keys():
            ships[esi_ship_result['ship_item_id']] = basic_pilot
            ships[esi_ship_result['ship_item_id']]['ship_type'] = supers[esi_ship_result['ship_type_id']]
            ships[esi_ship_result['ship_item_id']]['super_type'] = "Supercarrier"
            ships[esi_ship_result['ship_item_id']]['main'] = main
            ships[esi_ship_result['ship_item_id']]['active'] = True

        if esi_ship_result['ship_item_id'] in ships:

            request_location_url = 'characters/{}/location/?datasource=tranquility'.format(uid)
            esi_location_code, esi_location_result = common.request_esi.esi(__name__, request_location_url,
                                                                            method='get',
                                                                            charid=uid)

            if esi_location_code != 200:
                # something broke severely
                _logger.log('[' + __name__ + '] location API error {0}: {1}'.format(esi_location_code,
                                                                                    esi_location_result['error']),
                            _logger.LogLevel.ERROR)
                error = esi_location_result['error']
                err_result = {'code': esi_location_code, 'error': error}
                raise Exception(error)

            if 'structure_id' in esi_location_result:
                request_assets_url = 'universe/structures/{}/?datasource=tranquility'\
                    .format(esi_location_result['structure_id'])
                esi_structure_code, esi_structure_result = common.request_esi.esi(__name__, request_assets_url,
                                                                                  method='get', charid=uid)

                if esi_structure_code == 401 or esi_structure_code == 403:
                    ships[esi_ship_result['ship_item_id']]['location'] = 'UNAUTHORIZED STRUCTURE'
                else:
                    if esi_structure_code != 200:
                        # something broke severely
                        _logger.log('[' + __name__ + '] asset API error {0}: {1}'.format(esi_structure_code,
                                                                                         esi_structure_result[
                                                                                             'error']),
                                    _logger.LogLevel.ERROR)
                        error = esi_structure_result['error']
                        err_result = {'code': esi_structure_code, 'error': error}
                        raise Exception(error)

                    request_sys_url = 'universe/systems/{}/?datasource=tranquility'.format(
                        esi_structure_result['solar_system_id'])
                    esi_system_code, esi_system_result = common.request_esi.esi(__name__, request_sys_url,
                                                                                method='get', charid=uid)

                    if esi_system_code != 200:
                        # something broke severely
                        _logger.log(
                            '[' + __name__ + '] ship API error {0}: {1}'.format(esi_system_code,
                                                                                esi_system_result['error']),
                            _logger.LogLevel.ERROR)
                        error = esi_system_result['error']
                        err_result = {'code': esi_system_code, 'error': error}
                        raise Exception(error)

                    ships[esi_ship_result['ship_item_id']]['location'] = esi_system_result['name'] + ' (Docked)'
            else:
                request_sys_url = 'universe/systems/{}/?datasource=tranquility'.format(
                    esi_location_result['solar_system_id'])
                esi_system_code, esi_system_result = common.request_esi.esi(__name__, request_sys_url, method='get')

                if esi_system_code != 200:
                    # something broke severely
                    _logger.log(
                        '[' + __name__ + '] ship API error {0}: {1}'.format(esi_system_code, esi_system_result['error']),
                        _logger.LogLevel.ERROR)
                    error = esi_system_result['error']
                    err_result = {'code': esi_system_code, 'error': error}
                    raise Exception(error)

                ships[esi_ship_result['ship_item_id']]['location'] = esi_system_result['name']
        elif 1==1:
            # check if asset scope is available
            scope_code, _ = _check_scope.check_scope(__name__, uid, ['esi-assets.read_assets.v1'])

            if scope_code:
                request_assets_url = 'characters/{}/assets/?datasource=tranquility'.format(uid)
                esi_assets_code, esi_assets_result = common.request_esi.esi(__name__, request_assets_url,
                                                                            method='get',
                                                                            charid=uid)
                if esi_assets_code != 200:
                    # something broke severely
                    _logger.log('[' + __name__ + '] asset API error {0}: {1}'.format(esi_assets_code,
                                                                                     esi_assets_result['error']),
                                _logger.LogLevel.ERROR)
                    error = esi_assets_result['error']
                    err_result = {'code': esi_assets_code, 'error': error}
                    raise Exception(error)

                for asset in esi_assets_result:
                    if asset['type_id'] in titans.keys():
                        ships[asset['item_id']] = basic_pilot
                        ships[asset['item_id']]['ship_type'] = titans[asset['type_id']]
                        ships[asset['item_id']]['super_type'] = "Titan"
                        ships[asset['item_id']]['main'] = main
                        ships[asset['item_id']]['active'] = False
                        ships[asset['item_id']]['location'] = "Unknown"

                    elif asset['type_id'] in supers.keys():
                        ships[asset['item_id']] = basic_pilot
                        ships[asset['item_id']]['ship_type'] = supers[asset['type_id']]
                        ships[asset['item_id']]['super_type'] = "Supercarrier"
                        ships[asset['item_id']]['main'] = main
                        ships[asset['item_id']]['active'] = False
                        ships[asset['item_id']]['location'] = "Unknown"

                    if asset['item_id'] in ships:
                        location_id = asset['location_type']
                        location_type = asset['location_type']

                        if location_type == "other":
                            request_assets_url = 'universe/structures/{}/?datasource=tranquility'.format(location_id)
                            esi_structure_code, esi_structure_result = common.request_esi.esi(__name__, request_assets_url,
                                                                                              method='get', charid=uid)

                            if esi_structure_code == 401 or esi_structure_code == 403:
                                ships[asset['item_id']]['location'] = 'UNAUTHORIZED STRUCTURE'
                            else:
                                if esi_structure_code != 200:
                                    # something broke severely
                                    _logger.log('[' + __name__ + '] asset API error {0}: {1}'.format(esi_structure_code,
                                                                                                     esi_structure_result[
                                                                                                         'error']),
                                                _logger.LogLevel.ERROR)
                                    error = esi_structure_result['error']
                                    err_result = {'code': esi_structure_code, 'error': error}
                                    ships[asset['item_id']]['location'] = 'ERROR'
                                else:
                                    request_sys_url = 'universe/systems/{}/?datasource=tranquility'.format(
                                        esi_structure_result['solar_system_id'])
                                    esi_system_code, esi_system_result = common.request_esi.esi(__name__, request_sys_url,
                                                                                                method='get', charid=uid)

                                    if esi_system_code != 200:
                                        # something broke severely
                                        _logger.log(
                                            '[' + __name__ + '] ship API error {0}: {1}'.format(esi_system_code,
                                                                                                esi_system_result['error']),
                                            _logger.LogLevel.ERROR)
                                        error = esi_system_result['error']
                                        err_result = {'code': esi_system_code, 'error': error}
                                        raise Exception(error)

                                    ships[asset['item_id']]['location'] = esi_system_result['name'] + ' (Docked)'

            else:
                _logger.log(
                    '[' + __name__ + '] no asset scope for char {}'.format(uid), _logger.LogLevel.WARNING)
        if len(ships) > 0:
            request_url = 'corporations/{}/?datasource=tranquility'.format(corpid)
            esi_code, esi_result = common.request_esi.esi(__name__, request_url, method='get')

            if not esi_code == 200:
                # something broke severely
                _logger.log('[' + __name__ + '] corporation API error {0}: {1}'.format(esi_code, esi_result['error']),
                            _logger.LogLevel.ERROR)
                error = esi_result['error']
                err_result = {'code': esi_code, 'error': error}
                raise Exception(error)

            corp_name = esi_result['corporation_name']

            for id in ships:
                ships[id]['corporation'] = corp_name

    return ships
