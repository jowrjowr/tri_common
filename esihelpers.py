from common.check_role import check_role
import common.logger as _logger
import common.check_scope as _check_scope
import common.request_esi
import urllib


def esi_affiliations(charid):
    # a more complete ESI affiliations check

    affiliations = dict()

    # character info

    request_url = 'characters/{0}/?datasource=tranquility'.format(charid)
    code, result = common.request_esi.esi(__name__, request_url, method='get', version='v4')
    if not code == 200:
        error = result['error']
        _logger.log('[' + __name__ + '] unable to get character info for {0}: {1}'.format(charid, error),_logger.LogLevel.ERROR)
        affiliations['error'] = error
        return affiliations

    affiliations['charname'] = result['name']
    affiliations['corpid'] = result.get('corporation_id')

    # alliance id, if any
    request_url = 'corporations/{0}/?datasource=tranquility'.format(affiliations['corpid'])
    code, result = common.request_esi.esi(__name__, request_url, method='get', version='v3')
    if not code == 200:
        error = result['error']
        _logger.log('[' + __name__ + '] unable to get corp info for {0}: {1}'.format(charid, error),_logger.LogLevel.ERROR)
        affiliations['allianceid'] = False
        affiliations['error'] = error
        return affiliations

    affiliations['allianceid'] = result.get('alliance_id')
    affiliations['corpname'] = result.get('corporation_name')

    if not affiliations['allianceid']:
        # no alliance so we're done getting information
        affiliations['alliancename'] = None
        return affiliations

    # alliance name
    request_url = 'alliances/{0}/?datasource=tranquility'.format(affiliations['allianceid'])
    code, result = common.request_esi.esi(__name__, request_url, method='get', version='v2')
    if not code == 200:
        error = result['error']
        _logger.log('[' + __name__ + '] unable to get alliance info for {0}: {1}'.format(affiliations['allianceid'], error),_logger.LogLevel.ERROR)
        affiliations['alliancename'] = False
        affiliations['error'] = error
        return affiliations
    affiliations['alliancename'] = result.get('alliance_name')

    return affiliations

def user_search(charname):
    # use esi search to find character

    query = { 'categories': 'character', 'datasource': 'tranquility', 'language': 'en-us', 'search': charname, 'strict': 'true' }
    query = urllib.parse.urlencode(query)
    esi_url = 'search/?' + query
    code, result = common.request_esi.esi(__name__, esi_url, method='get', version='v1')
    _logger.log('[' + __name__ + '] /search output: {}'.format(result), _logger.LogLevel.DEBUG)

    if not code == 200:
        _logger.log('[' + __name__ + '] error searching for user {0}: {1}'.format(charname, result['error']),_logger.LogLevel.INFO)
        return False
    else:
        # quantify the result
        _logger.log('[' + __name__ + '] found {0} matches for "{1}"'.format(len(result), charname),_logger.LogLevel.DEBUG)

    return result

def current_ship(charid):
    
    # fetch the current ship typeID charid is flying
    
    # check if ship scope is available
    
    test_scopes = ['esi-location.read_ship_type.v1']
    scope_code, result = _check_scope.check_scope(__name__, charid, test_scopes)

    if scope_code == False:
        # does not have proper scopes
        msg = 'character {0} missing ESI scopes: {1}'.format(charid, result)
        _logger.log('[' + __name__ + '] ' + msg,_logger.LogLevel.WARNING)
        return False, None
        
    # fetch current ship
    request_ship_url = 'characters/{}/ship/?datasource=tranquility'.format(charid)
    esi_ship_code, esi_ship_result = common.request_esi.esi(__name__, request_ship_url, version='v1', method='get', charid=charid)
    _logger.log('[' + __name__ + '] /characters output: {}'.format(esi_ship_result), _logger.LogLevel.DEBUG)

    if esi_ship_code != 200:
        # something broke severely
        _logger.log('[' + __name__ + '] /characters/ship API error {0}: {1}'.format(esi_ship_code, esi_ship_result['error']),_logger.LogLevel.WARNING)
        return False, None
        
    return True, esi_ship_result

def find_types(charid, types):
    # look through character assets to find matching typeids
    
    # check if ship scope is available
    
    test_scopes = ['esi-assets.read_assets.v1']
    scope_code, result = _check_scope.check_scope(__name__, charid, test_scopes)

    if scope_code == False:
        # does not have proper scopes
        msg = 'character {0} missing ESI scopes: {1}'.format(charid, result)
        _logger.log('[' + __name__ + '] ' + msg,_logger.LogLevel.WARNING)
        return False, None
        
    request_assets_url = 'characters/{}/assets/?datasource=tranquility'.format(charid)
    esi_assets_code, esi_assets_result = common.request_esi.esi(__name__, request_assets_url, version='v1', method='get', charid=charid)
    _logger.log('[' + __name__ + '] /characters output: {}'.format(esi_assets_result), _logger.LogLevel.DEBUG)
    if esi_assets_code != 200:
        _logger.log('[' + __name__ + '] /characters/assets API error {0}: {1}'.format(esi_assets_code, esi_assets_result['error']),_logger.LogLevel.WARNING)
        return False, None
        
    # locate the typeids in question

    asset_result = []

    for asset in esi_assets_result:
        if asset['type_id'] in types:
            asset_result.append(asset)

    return True, asset_result
    
def char_location(charid):

    # check if location scope is available

    test_scopes = ['esi-location.read_online.v1']
    scope_code, result = _check_scope.check_scope(__name__, charid, test_scopes)

    if scope_code == False:
        # does not have proper scopes
        msg = 'character {0} missing ESI scopes: {1}'.format(charid, result)
        _logger.log('[' + __name__ + '] ' + msg,_logger.LogLevel.WARNING)
        return False, None

    # fetch character location
    request_url = 'characters/{0}/location/?datasource=tranquility'.format(charid)
    code, result = common.request_esi.esi(__name__, request_url, method='get', charid=charid, version='v1')
    _logger.log('[' + __name__ + '] /characters output: {}'.format(result), _logger.LogLevel.DEBUG)

    if not code == 200:
        _logger.log('[' + __name__ + '] /characters location API error {0}: {1}'.format(code, result['error']), _logger.LogLevel.WARNING)
        return False, None

    location_id = result.get('solar_system_id')
    structure_id = result.get('structure_id')
    station_id = result.get('station_id')

    # map the solar system to a name

    request_url = 'universe/systems/{0}/?datasource=tranquility'.format(location_id)
    code, result = common.request_esi.esi(__name__, request_url, method='get', version='v3')
    _logger.log('[' + __name__ + '] /universe/systems output: {}'.format(result), _logger.LogLevel.DEBUG)
    if not code == 200:
        _logger.log('[' + __name__ + '] /universe/systems API error ' + str(code) + ': ' + str(result['error']), _logger.LogLevel.WARNING)
        location_name = 'Unknown'
    else:
        location_name = result['name']

    # map the structure to a name

    if structure_id is not None:
        # resolve a structure name
        request_url = 'universe/structures/{}/?datasource=tranquility'.format(structure_id)
        code, result = common.request_esi.esi(__name__, request_url, method='get', version='v1', charid=charid)
        _logger.log('[' + __name__ + '] /universe/structures output: {}'.format(result), _logger.LogLevel.DEBUG)
        if code == 200:
            structure_name = result['name']
        elif code == 403:
            # unable to resolve structure name if the character has no ACL
            structure_name = 'UNAUTHORIZED STRUCTURE'
        else:
            _logger.log('[' + __name__ + '] /universe/systems API error ' + str(code) + ': ' + str(result['error']), _logger.LogLevel.WARNING)
            structure_name = 'Unknown'
    if station_id is not None:
        request_url = 'universe/names/?datasource=tranquility'
        data = '[{}]'.format(station_id)
        code, result = common.request_esi.esi(__name__, request_url, method='post', version='v2', data=data)
        _logger.log('[' + __name__ + '] /universe/structures output: {}'.format(result), _logger.LogLevel.DEBUG)
        if code == 200:
            structure_name = result[0]['name']
        else:
            print(type(station_id))
            _logger.log('[' + __name__ + '] /universe/systems API error ' + str(code) + ': ' + str(result['error']), _logger.LogLevel.WARNING)
            structure_name = 'Unknown'

    else:
        structure_name = None

    char_location = dict()
    char_location['location_id'] = location_id
    char_location['location'] = location_name
    char_location['structure_id'] = structure_id
    char_location['structure_name'] = structure_name
    char_location['station_id'] = station_id

    return True, char_location


def character_info(char_id):

    request_url = 'characters/{0}/?datasource=tranquility'.format(char_id)
    code, result = common.request_esi.esi(__name__, request_url, method='get', version='v1')

    if not code == 200:
        _logger.log('[' + __name__ + '] /characters/ID API error ' + str(code) + ': ' + str(result['error']),
                    _logger.LogLevel.WARNING)
        return False

    return result


def corporation_info(corp_id):

    if corp_id == None:
        return None

    request_url = 'corporations/{0}/?datasource=tranquility'.format(corp_id)
    code, result = common.request_esi.esi(__name__, request_url, method='get', version='latest')

    if not code == 200:
        _logger.log('[' + __name__ + '] /corporations/{0} API error '
                    .format(corp_id) + str(code) + ': ' + str(result['error']),
                    _logger.LogLevel.WARNING)
        return False

    return result


def alliance_info(alliance_id):

    if alliance_id == None:
        return None

    request_url = 'alliances/{0}/?datasource=tranquility'.format(alliance_id)
    code, result = common.request_esi.esi(__name__, request_url, method='get', version='v1')

    if not code == 200:
        _logger.log('[' + __name__ + '] /alliances/ID API error ' + str(code) + ': ' + str(result['error']),
                    _logger.LogLevel.WARNING)
        return False

    return result
