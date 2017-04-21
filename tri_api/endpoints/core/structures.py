def core_structures():

    from flask import Flask, request, url_for, json, Response
    from joblib import Parallel, delayed

    import common.logger as _logger
    import MySQLdb as mysql
    import common.database as DATABASE
    import common.request_esi
    import requests
    import json

    # CONSTANTS TO MOVE OUT
    baseurl = 'https://esi.tech.ccp.is/latest/'

    # attempt mysql connection (abort in case of failure)
    try:
        sql_conn = mysql.connect(
            database=DATABASE.DB_DATABASE,
            user=DATABASE.DB_USERNAME,
            password=DATABASE.DB_PASSWORD,
            host=DATABASE.DB_HOST)
    except mysql.Error as err:
        js = json.dumps({ 'code': -1, 'error': 'unable to connect to mysql: ' + str(err)})
        _logger.log('[' + __name__ + '] unable to connect to mysql:'.format(err), _logger.LogLevel.ERROR)
        resp = Response(js, status=500, mimetype='application/json')
        return resp

    # get all the structure shit for the char in question

    if 'id' not in request.args:
        js = json.dumps({ 'code': -1, 'error': 'need an id to check'})
        _logger.log('[' + __name__ + '] need an id to check', _logger.LogLevel.WARNING)
        resp = Response(js, status=401, mimetype='application/json')
        return resp
    _logger.log('[' + __name__ + '] querying structures for {0}'.format(request.args['id']), _logger.LogLevel.INFO)


    # filtering garbage requires exception catching, as it turns out...

    try:
        id = int(request.args['id'])
    except ValueError:
        js = json.dumps({ 'code': -1, 'error': 'id parameter must be integer'})
        _logger.log('[' + __name__ + '] id parameters must be integer: {0}'.format(id), _logger.LogLevel.WARNING)
        resp = Response(js, status=401, mimetype='application/json')
        return resp

    cursor = sql_conn.cursor()
    query = 'SELECT accessToken FROM CrestTokens WHERE charID = %s'

    try:
        row_count = cursor.execute(query, (id,))

        # no row, no token, nothing to do.
        if row_count == 0:
            cursor.close()
            js = json.dumps({ 'code': -1, 'error': 'no token for charid ' + str(id) })
            _logger.log('[' + __name__ + '] no token for charid: {0}'.format(charid), _logger.LogLevel.WARNING)
            resp = Response(js, status=404, mimetype='application/json')
            return resp

        row = cursor.fetchone()
        atoken = row[0].decode("utf-8")

    except Exception as errmsg:
        cursor.close()
        js = json.dumps({ 'code': -1, 'error': 'mysql broke: ' + str(errmsg)})
        _logger.log('[' + __name__ + '] mysql broke:'.format(errmsg), _logger.LogLevel.ERROR)
        resp = Response(js, status=500, mimetype='application/json')
        return resp

    # get corpid
    request_url = baseurl + 'characters/affiliation/?datasource=tranquility'
    data = '[{}]'.format(id)
    code, result = common.request_esi.esi(__name__, request_url, 'post', data)
    if not code == 200:
        _logger.log('[' + __name__ + '] unable to get character affiliations for {0}: {1}'.format(charid, error),_logger.LogLevel.ERROR)
        return(False, 'error')

    corpid = result[0]['corporation_id']

    esi_url = baseurl + 'corporations/' + str(corpid)
    esi_url = esi_url + '/structures?datasource=tranquility'
    esi_url = esi_url + '&token=' + atoken

    # get all structures that this token has access to
    print(esi_url)
    # do the request, but catch exceptions for connection issues
    code, result_parsed = common.request_esi.esi(__name__, esi_url, 'get')
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
        structures[structure_id] = structure_parse(baseurl, atoken, object, structure_id)
    sql_conn.close()
    return json.dumps(structures)

def structure_parse(baseurl, atoken, object, structure_id):

    import common.logger as _logger
    import MySQLdb as mysql
    import common.database as DATABASE
    import common.request_esi
    import requests
    import json

    structure = {}
    try:
        structure['fuel_expires'] = object['fuel_expires']
    except:
        # there seems to be no fuel key if there are no services
        # unclear on what happens if there are services but no fuel
        structure['fuel_expires'] = 'N/A'

    structure['structure_id'] = structure_id

    esi_url = baseurl + 'universe/structures/' + str(structure_id)
    esi_url = esi_url + '?datasource=tranquility'
    esi_url = esi_url + '&token=' + atoken

    code, data = common.request_esi.esi(__name__, esi_url, 'get')
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
    esi_url = baseurl + 'universe/types/' + str(typeid)
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
    esi_url = baseurl + 'universe/systems/' + str(system_id)
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

    esi_url = baseurl + 'universe/constellations/'+str(constellation_id)
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
    esi_url = baseurl + 'universe/regions/'+str(region_id)
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
