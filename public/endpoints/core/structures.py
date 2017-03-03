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
        resp = Response(js, status=500, mimetype='application/json')
        return resp

    # get all the structure shit for the char in question

    if 'id' not in request.args:
        js = json.dumps({ 'code': -1, 'error': 'need an id to check'})
        resp = Response(js, status=401, mimetype='application/json')
        return resp

    # filtering garbage requires exception catching, as it turns out...

    try:
        id = int(request.args['id'])
    except ValueError:
        js = json.dumps({ 'code': -1, 'error': 'id parameter must be integer'})
        resp = Response(js, status=401, mimetype='application/json')
        return resp

    cursor = sql_conn.cursor()
    query = 'SELECT charID,corpID,accessToken,refreshToken FROM CrestTokens WHERE charID = %s'
    # the forced-tuple on (id,) is deliberate due to mysqldb weirdness
    try:
        row_count = cursor.execute(query, (id,))

        # no row, no token, nothing to do.
        if row_count == 0:
            cursor.close()
            js = json.dumps({ 'code': -1, 'error': 'no token for charid ' + str(id) })
            resp = Response(js, status=404, mimetype='application/json')
            return resp

        row = cursor.fetchone()
        charid = row[0]
        corpid = row[1]
        atoken = row[2].decode("utf-8")
        rtoken = row[3].decode("utf-8")

    except Exception as errmsg:
        cursor.close()
        js = json.dumps({ 'code': -1, 'error': 'mysql broke: ' + str(errmsg)})
        resp = Response(js, status=500, mimetype='application/json')
        return resp

    esi_url = baseurl + 'corporations/' + str(corpid)
    esi_url = esi_url + '/structures?datasource=tranquility'
    esi_url = esi_url + '&token=' + atoken

    # get all structures that this token has access to

    # do the request, but catch exceptions for connection issues
    try:
        request = common.request_esi.esi(__name__, esi_url)
    except common.request_esi.NotHttp200 as error:
        # something broke severely
        _logger.log('[' + __name__ + '] /structures API error ' + str(error.code) + ': ' + str(error.message), _logger.LogLevel.ERROR)
        resp = Response(error.message, status=error.code, mimetype='application/json')
        return resp
    result_parsed = json.loads(request)

    structures = {}

    # get name of structures and build the structure dictionary

# parallelize this with joblib

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

    try:
        request = common.request_esi.esi(__name__, esi_url)
    except common.request_esi.NotHttp200 as error:
        _logger.log('[' + __name__ + '] /structures API error ' + str(error.code) + ': ' + str(error.message), _logger.LogLevel.ERROR)
        # kinder, gentler error handling
        pass
    data = json.loads(request)

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

    try:
        request = common.request_esi.esi(__name__, esi_url)
    except common.request_esi.NotHttp200 as error:
        _logger.log('[' + __name__ + '] /universe/types API error ' + str(error.code) + ': ' + str(error.message), _logger.LogLevel.ERROR)
        # kinder, gentler error handling
        pass
    typedata = json.loads(request)

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

    try:
        request = common.request_esi.esi(__name__, esi_url)
    except common.request_esi.NotHttp200 as error:
        # kinder, gentler error handling
        _logger.log('[' + __name__ + '] /universe/systems API error ' + str(error.code) + ': ' + str(error.message), _logger.LogLevel.ERROR)
        pass
    data = json.loads(request)

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

    try:
        request = common.request_esi.esi(__name__, esi_url)
    except common.request_esi.NotHttp200 as error:
        # kinder, gentler error handling
        _logger.log('[' + __name__ + '] /universe/constellations API error ' + str(error.code) + ': ' + str(error.message), _logger.LogLevel.ERROR)
        pass
    data = json.loads(request)

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

    try:
        request = common.request_esi.esi(__name__, esi_url)
    except common.request_esi.NotHttp200 as error:
        # kinder, gentler error handling
        _logger.log('[' + __name__ + '] /universe/regions API error ' + str(error.code) + ': ' + str(error.message), _logger.LogLevel.ERROR)
        pass
    data = json.loads(request)

    try:
        structure['region'] = data['name']
    except:
        structures[structure_id] = structure
        error = data['error']
        error_code = data['code']
        return structure

    return structure
