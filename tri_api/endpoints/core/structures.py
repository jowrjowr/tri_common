from flask import request
from tri_api import app

@app.route('/core/structures', methods=['GET'])
def core_structures():

    from flask import Flask, request, Response
    from joblib import Parallel, delayed

    from common.api import base_url
    import common.logger as _logger
    import common.request_esi
    import json

    # get all the structure shit for the char in question

    if 'id' not in request.args:
        js = json.dumps({ 'error': 'need an id to check'})
        _logger.log('[' + __name__ + '] need an id to check', _logger.LogLevel.WARNING)
        resp = Response(js, status=401, mimetype='application/json')
        return resp
    _logger.log('[' + __name__ + '] querying structures for {0}'.format(request.args['id']), _logger.LogLevel.INFO)


    # filtering garbage requires exception catching, as it turns out...

    try:
        id = int(request.args['id'])
    except ValueError:
        _logger.log('[' + __name__ + '] id parameters must be integer: {0}'.format(id), _logger.LogLevel.WARNING)
        js = json.dumps({ 'error': 'id parameter must be integer'})
        resp = Response(js, status=401, mimetype='application/json')
        return resp

    # query character roles to determine if they are allowed to look at corp structures
    request_url = base_url + 'characters/{0}/roles/?datasource=tranquility'.format(id)
    code, result = common.request_esi.esi(__name__, request_url, method='get', charid=id)
    if not code == 200:
        error = 'unable to get character roles for {0}: ({1}) {2}'.format(id, code, result['error'])
        _logger.log('[' + __name__ + ']' + error,_logger.LogLevel.ERROR)
        js = json.dumps({ 'error': error})
        resp = Response(js, status=500, mimetype='application/json')
        return resp

    # this should be enough? not sure what CEO gives you

    allowed = False
    allowed_roles = ['Director', 'Station_Manager']

    for role in result:
        if role in allowed_roles:
            allowed = True

    if allowed == False:
        error = 'insufficient corporate roles to access this endpoint.'
        _logger.log('[' + __name__ + ']' + error,_logger.LogLevel.INFO)
        js = json.dumps({ 'error': error})
        resp = Response(js, status=403, mimetype='application/json')
        return resp
    else:
        _logger.log('[' + __name__ + '] sufficient roles to view corp structure information',_logger.LogLevel.DEBUG)

    # get corpid
    request_url = base_url + 'characters/affiliation/?datasource=tranquility'
    data = '[{}]'.format(id)
    code, result = common.request_esi.esi(__name__, request_url, method='post', data=data)
    if not code == 200:
        _logger.log('[' + __name__ + '] unable to get character affiliations for {0}: {1}'.format(charid, error),_logger.LogLevel.ERROR)
        return(False, 'error')

    corpid = result[0]['corporation_id']

    esi_url = base_url + 'corporations/' + str(corpid)
    esi_url = esi_url + '/structures?datasource=tranquility'

    # get all structures that this user has access to

    code, result_parsed = common.request_esi.esi(__name__, esi_url, 'get', charid=id)
    if not code == 200:
        # something broke severely
        _logger.log('[' + __name__ + '] /structures API error ' + str(code) + ': ' + str(result_parsed['error']), _logger.LogLevel.ERROR)
        resp = Response(result_parsed['error'], status=code, mimetype='application/json')
        return resp

    _logger.log('[' + __name__ + '] /structures output:'.format(result_parsed), _logger.LogLevel.DEBUG)

    try:
        errormsg = result_parsed['error']
        resp = Response(errormsg, status=403, mimetype='application/json')
        return resp
    except Exception:
        pass

    # get name of structures and build the structure dictionary

    structures = dict()

    for object in result_parsed:
        structure_id = object['structure_id']
        structures[structure_id] = structure_parse(id, object, structure_id)
    return json.dumps(structures)

def structure_parse(charid, object, structure_id):

    import common.logger as _logger
    from common.api import base_url
    import common.database as DATABASE
    import common.request_esi
    import json

    structure = {}
    try:
        structure['fuel_expires'] = object['fuel_expires']
    except:
        # there seems to be no fuel key if there are no services
        # unclear on what happens if there are services but no fuel
        structure['fuel_expires'] = 'N/A'

    structure['structure_id'] = structure_id

    esi_url = base_url + 'universe/structures/' + str(structure_id)
    esi_url = esi_url + '?datasource=tranquility'

    code, data = common.request_esi.esi(__name__, esi_url, method='get', charid=charid)
    if not code == 200:
        # something broke severely
        _logger.log('[' + __name__ + '] /structures API error ' + str(code) + ': ' + str(data['error']), _logger.LogLevel.ERROR)
        resp = Response(result['error'], status=code, mimetype='application/json')
        return resp

    # catch errors

    try:
        structure['name'] = data['name']
    except:
        # try a graceful fail
        structure['name'] = 'Unknown'
        structure['system'] = 'Unknown'
        structure['region'] = 'Unknown'
        error = data['error']
        error_code = data['code']
        return structure


    # get structure type name

    typeid = data['type_id']
    esi_url = base_url + 'universe/types/{0}'.format(typeid)
    esi_url = esi_url + '?datasource=tranquility'

    code, typedata = common.request_esi.esi(__name__, esi_url, 'get')
    if not code == 200:
        # something broke severely
        _logger.log('[' + __name__ + '] /universe/types API error ' + str(code) + ': ' + str(typedata['error']), _logger.LogLevel.ERROR)
        resp = Response(result['error'], status=code, mimetype='application/json')
        return resp

    try:
        structure['type_name'] = typedata['name']
    except:
        structure['type_name'] = 'Unknown'
        return structure


    # get solar system info
    # step 1: get name and constellation

    system_id = data['solar_system_id']
    esi_url = base_url + 'universe/systems/{0}/'.format(system_id)
    esi_url = esi_url + '?datasource=tranquility'

    code, data = common.request_esi.esi(__name__, esi_url, 'get')
    if not code == 200:
        # something broke severely
        _logger.log('[' + __name__ + '] /universe/systems API error ' + str(code) + ': ' + str(data['error']), _logger.LogLevel.ERROR)
        resp = Response(result['error'], status=code, mimetype='application/json')
        return resp

    try:
        constellation_id = data['constellation_id']
        structure['system'] = data['name']
    except:
        structures[structure_id] = structure
        error = data['error']
        error_code = data['code']
        return structure

    # step 2: get the constellation info

    esi_url = base_url + 'universe/constellations/{0}'.format(constellation_id)
    esi_url = esi_url + '?datasource=tranquility'

    code, data = common.request_esi.esi(__name__, esi_url, 'get')
    if not code == 200:
        # something broke severely
        _logger.log('[' + __name__ + '] /universe/constellations API error ' + str(code) + ': ' + str(data['error']), _logger.LogLevel.ERROR)
        resp = Response(result['error'], status=code, mimetype='application/json')
        return resp

    try:
        region_id = data['region_id']
    except:
        structures[structure_id] = structure
        error = data['error']
        error_code = data['code']
        return structure

    # step 3: get region name
    esi_url = base_url + 'universe/regions/{0}/'.format(region_id)
    esi_url = esi_url + '?datasource=tranquility'

    code, data = common.request_esi.esi(__name__, esi_url, 'get')
    if not code == 200:
        # something broke severely
        _logger.log('[' + __name__ + '] /universe/regions API error ' + str(code) + ': ' + str(data['error']), _logger.LogLevel.ERROR)
        resp = Response(result['error'], status=code, mimetype='application/json')
        return resp

    try:
        structure['region'] = data['name']
    except:
        structures[structure_id] = structure
        error = data['error']
        error_code = data['code']
        return structure

    return structure
