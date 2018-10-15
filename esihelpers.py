import common.logger as _logger
import common.request_esi
import urllib
from common.check_scope import check_scope

def region_solar_systems(region_id):
    # spew out every solar system in a region

    info = dict()
    info['error'] = False
    info['region_id'] = region_id
    info['systems'] = dict()

    request_url = 'universe/regions/{0}'.format(region_id)
    code, result = common.request_esi.esi(__name__, request_url, version='v1')

    if not code == 200:
        info['error'] = True
        msg = '/universe/regions error: {0}'.format(result['error'])
        _logger.log('[' + __name__ + '] {0}'.format(msg),_logger.LogLevel.ERROR)
        return info

    for constellation_id in result['constellations']:
        request_url = 'universe/constellations/{0}'.format(constellation_id)
        code, result = common.request_esi.esi(__name__, request_url, version='v1')
        if not code == 200:
            info['error'] = True
            msg = '/universe/constellation error: {0}'.format(result['error'])
            _logger.log('[' + __name__ + '] {0}'.format(msg),_logger.LogLevel.ERROR)
            return info
        for system in result['systems']:

            # fetch info

            info['systems'][system] = solar_system_info(system)

    return info

def esi_affiliations(charid):
    # a more complete ESI affiliations check

    affiliations = dict()

    # character info

    request_url = 'characters/{0}/'.format(charid)
    code, result = common.request_esi.esi(__name__, request_url, method='get', version='v4')
    if code == 404:
        # 404's are a problem but not an ERROR problem
        error = result
        _logger.log('[' + __name__ + '] unable to get character info for {0}: {1}'.format(charid, error),_logger.LogLevel.DEBUG)
        affiliations['error'] = True
        return affiliations
    elif not code == 200:
        error = result
        _logger.log('[' + __name__ + '] unable to get character info for {0}: {1}'.format(charid, error),_logger.LogLevel.ERROR)
        affiliations['error'] = True
        return affiliations

    affiliations['charname'] = result['name']
    affiliations['corpid'] = result.get('corporation_id')

    # alliance id, if any
    request_url = 'corporations/{0}/'.format(affiliations['corpid'])
    code, result = common.request_esi.esi(__name__, request_url, method='get', version='v4')
    if not code == 200:
        error = result['error']
        _logger.log('[' + __name__ + '] unable to get corp info for {0}: {1}'.format(charid, error),_logger.LogLevel.ERROR)
        affiliations['allianceid'] = False
        affiliations['error'] = error
        return affiliations

    affiliations['allianceid'] = result.get('alliance_id')
    affiliations['corpname'] = result.get('name')

    if not affiliations['allianceid']:
        # no alliance so we're done getting information
        affiliations['alliancename'] = None
        return affiliations

    # alliance name
    request_url = 'alliances/{0}/'.format(affiliations['allianceid'])
    code, result = common.request_esi.esi(__name__, request_url, method='get', version='v3')
    if not code == 200:
        error = result['error']
        _logger.log('[' + __name__ + '] unable to get alliance info for {0}: {1}'.format(affiliations['allianceid'], error),_logger.LogLevel.ERROR)
        affiliations['alliancename'] = False
        affiliations['error'] = error
        return affiliations
    affiliations['alliancename'] = result.get('name')

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
    result = check_scope(charid, test_scopes)

    if not result:
        # does not have proper scopes
        msg = 'character {0} missing ESI scopes: {1}'.format(charid, result)
        _logger.log('[' + __name__ + '] ' + msg,_logger.LogLevel.WARNING)
        return False, None
        
    # fetch current ship
    request_ship_url = 'characters/{}/ship/'.format(charid)
    esi_ship_code, esi_ship_result = common.request_esi.esi(__name__, request_ship_url, version='v1', method='get', charid=charid)
    _logger.log('[' + __name__ + '] /characters output: {}'.format(esi_ship_result), _logger.LogLevel.DEBUG)

    if esi_ship_code != 200:
        # something broke severely
        _logger.log('[' + __name__ + '] /characters/ship API error {0}: {1}'.format(esi_ship_code, esi_ship_result),_logger.LogLevel.WARNING)
        return False, None
        
    return True, esi_ship_result

def find_types(charid, types):
    # look through character assets to find matching typeids
    
    # check if ship scope is available
    
    test_scopes = ['esi-assets.read_assets.v1']
    result = check_scope(charid, test_scopes)

    if not result:
        # does not have proper scopes
        msg = 'character {0} missing ESI scopes: {1}'.format(charid, result)
        _logger.log('[' + __name__ + '] ' + msg,_logger.LogLevel.WARNING)
        return False, None
        
    request_assets_url = 'characters/{}/assets/'.format(charid)
    esi_assets_code, esi_assets_result = common.request_esi.esi(__name__, request_assets_url, version='v3', method='get', charid=charid)
    _logger.log('[' + __name__ + '] /characters output: {}'.format(esi_assets_result), _logger.LogLevel.DEBUG)
    if esi_assets_code != 200:
        _logger.log('[' + __name__ + '] /characters/assets API error {0}: {1}'.format(esi_assets_code, esi_assets_result),_logger.LogLevel.WARNING)
        return False, None
        
    # locate the typeids in question

    asset_result = []

    for asset in esi_assets_result:
        if asset['type_id'] in types:
            asset_result.append(asset)

    return True, asset_result

def solar_system_info(solar_system_id):

    # return all the useful solar system info in one shot

    info = dict()
    info['error'] = False

    # solar system level info

    request_url = 'universe/systems/{0}/'.format(solar_system_id)
    code, result = common.request_esi.esi(__name__, request_url, method='get', version='v4')
    _logger.log('[' + __name__ + '] /universe/systems output: {}'.format(result), _logger.LogLevel.DEBUG)
    if not code == 200:
        msg = '/universe/systems api error {0}: {1}'.format(code, result.get('error'))
        _logger.log('[' + __name__ + '] {}'.format(msg), _logger.LogLevel.WARNING)
        info['error'] = True
        info['solar_system_name'] = 'Unknown'
        return info
    else:
        info['constellation_id'] = result['constellation_id']
        info['solar_system_name'] = result['name']

    # constellation level info

    request_url = 'universe/constellations/{0}/'.format(info['constellation_id'])
    code, result = common.request_esi.esi(__name__, request_url, method='get', version='v1')
    _logger.log('[' + __name__ + '] /universe/constellations output: {}'.format(result), _logger.LogLevel.DEBUG)
    if not code == 200:
        msg = '/universe/constellations api error {0}: {1}'.format(code, result.get('error'))
        _logger.log('[' + __name__ + '] {}'.format(msg), _logger.LogLevel.WARNING)
        info['error'] = True
        info['constellation_name'] = 'Unknown'
        return info
    else:
        info['region_id'] = result['region_id']
        info['constellation_name'] = result['name']

    # region level info

    request_url = 'universe/regions/{0}/'.format(info['region_id'])
    code, result = common.request_esi.esi(__name__, request_url, method='get', version='v1')
    _logger.log('[' + __name__ + '] /universe/regions output: {}'.format(result), _logger.LogLevel.DEBUG)
    if not code == 200:
        msg = '/universe/regions api error {0}: {1}'.format(code, result.get('error'))
        _logger.log('[' + __name__ + '] {}'.format(msg), _logger.LogLevel.WARNING)
        info['error'] = True
        info['region_name'] = 'Unknown'
        return info
    else:
        info['region_name'] = result['name']

    return info

def char_location(charid):

    # check if location scope is available

    test_scopes = ['esi-location.read_online.v1']
    result = check_scope(charid, test_scopes)

    if not result:
        # does not have proper scopes
        msg = 'character {0} missing ESI scopes: {1}'.format(charid, result)
        _logger.log('[' + __name__ + '] ' + msg,_logger.LogLevel.WARNING)
        return False, None

    # fetch character location
    request_url = 'characters/{0}/location/'.format(charid)
    code, result = common.request_esi.esi(__name__, request_url, method='get', charid=charid, version='v1')
    _logger.log('[' + __name__ + '] /characters output: {}'.format(result), _logger.LogLevel.DEBUG)

    if not code == 200:
        _logger.log('[' + __name__ + '] /characters location API error {0}: {1}'.format(code, result), _logger.LogLevel.WARNING)
        return False, None

    location_id = result.get('solar_system_id')
    structure_id = result.get('structure_id')
    station_id = result.get('station_id')

    # map the solar system to a name

    location_info = solar_system_info(location_id)
    location_name = location_info.get('solar_system_name')

    # map the structure to a name

    if structure_id is not None:
        # resolve a structure name
        request_url = 'universe/structures/{}/'.format(structure_id)
        code, result = common.request_esi.esi(__name__, request_url, method='get', version='v2', charid=charid)
        _logger.log('[' + __name__ + '] /universe/structures output: {}'.format(result), _logger.LogLevel.DEBUG)
        if code == 200:
            structure_name = result['name']
        elif code == 403:
            # unable to resolve structure name if the character has no ACL
            structure_name = 'UNAUTHORIZED STRUCTURE'
        else:
            _logger.log('[' + __name__ + '] /universe/structures API error {0}: {1}'.format(code, result), _logger.LogLevel.WARNING)
            structure_name = 'Unknown'
    if station_id is not None:
        request_url = 'universe/names/'
        data = '[{}]'.format(station_id)
        code, result = common.request_esi.esi(__name__, request_url, method='post', version='v2', data=data)
        _logger.log('[' + __name__ + '] /universe/structures output: {}'.format(result), _logger.LogLevel.DEBUG)
        if code == 200:
            structure_name = result[0]['name']
        else:
            print(station_id)
            print(result)
            _logger.log('[' + __name__ + '] /universe/structures API error {0}: {1}'.format(code, result), _logger.LogLevel.WARNING)
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

def moon_info(moonid):

    request_url = 'universe/moons/{0}/'.format(moonid)

    code, result = common.request_esi.esi(__name__, request_url, 'get', version='v1')
    if not code == 200:
        # something broke severely
        msg = '/universe/moons API error {0}: {1}'.format(code, result['error'])
        _logger.log('[' + __name__ + '] {}'.format(msg), _logger.LogLevel.ERROR)

    return result

def type_info(typeid):

    request_url = 'universe/types/{0}/'.format(typeid)

    code, result = common.request_esi.esi(__name__, request_url, 'get', version='v3')
    if not code == 200:
        # something broke severely
        msg = '/universe/types API error {0}: {1}'.format(code, result['error'])
        _logger.log('[' + __name__ + '] {}'.format(msg), _logger.LogLevel.ERROR)

    return result

def character_info(char_id):

    request_url = 'characters/{0}/'.format(char_id)
    code, result = common.request_esi.esi(__name__, request_url, method='get', version='v4')

    if not code == 200:
        _logger.log('[' + __name__ + '] /characters/ID API error ' + str(code) + ': ' + str(result['error']),
                    _logger.LogLevel.WARNING)
        return False

    return result


def corporation_info(corp_id):

    if corp_id == None:
        return None

    request_url = 'corporations/{0}/'.format(corp_id)
    code, result = common.request_esi.esi(__name__, request_url, method='get', version='v4')

    if not code == 200:
        _logger.log('[' + __name__ + '] /corporations/{0} API error '
                    .format(corp_id) + str(code) + ': ' + str(result['error']),
                    _logger.LogLevel.WARNING)
        return False

    return result


def alliance_info(alliance_id):

    if alliance_id == None:
        return None

    request_url = 'alliances/{0}/'.format(alliance_id)
    code, result = common.request_esi.esi(__name__, request_url, method='get', version='v3')

    if not code == 200:
        _logger.log('[' + __name__ + '] /alliances/ID API error ' + str(code) + ': ' + str(result['error']),
                    _logger.LogLevel.WARNING)
        return False

    return result
