def core_isblue():

    from flask import Flask, request, url_for, json, Response
    from common.request_esi import request_esi
    import common.logger as _logger
    import MySQLdb as mysql
    import common.database as DATABASE
    import requests
    import json


    # core isblue function that tells whether a user, corp, or alliance is currently blue to triumvirate

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
        _logger.log('mysql error: ' + str(err), _logger.LogLevel.ERROR)
        js = json.dumps({ 'code': -1, 'error': 'unable to connect to mysql: ' + str(err)})
        resp = Response(js, status=500, mimetype='application/json')
        return resp

    if 'id' not in request.args:
        _logger.log('no id', _logger.LogLevel.WARNING)
        js = json.dumps({ 'code': -1, 'error': 'need an id to check'})
        resp = Response(js, status=401, mimetype='application/json')
        return resp

    # filtering garbage requires exception catching, as it turns out...

    try:
        id = int(request.args['id'])
    except ValueError:
        _logger.log('invalid id: ' + str(id), _logger.LogLevel.WARNING)
        js = json.dumps({ 'code': -1, 'error': 'id parameter must be integer'})
        resp = Response(js, status=401, mimetype='application/json')
        return resp

    # check through the core Permissions table to see if there's a match, as that's fast.

    cursor = sql_conn.cursor()
    query = 'SELECT allianceID,allianceName FROM Permissions WHERE allianceID = %s'

    # the forced-tuple on (id,) is deliberate due to mysqldb weirdness
    try:
        row = cursor.execute(query, (id,))
        cursor.close()
    except Exception as errmsg:
        _logger.log('mysql error: ' + str(errmsg), _logger.LogLevel.ERROR)
        js = json.dumps({ 'code': -1, 'error': 'mysql broke: ' + str(errmsg)})
        resp = Response(js, status=401, mimetype='application/json')
        return resp

    # if there's a nonzero return, that means the corp/alliance in question is blue to tri.
    # otherwise there's more processing to do.
    if row == 1:
        # BLUE! we're done.
        js = json.dumps({ 'code': 1 })
        resp = Response(js, status=200, mimetype='application/json')
        return resp

    # so neither blue as corp or alliance. let's try char.

    esi_url = baseurl + 'characters/' + str(id) + '/?datasource=tranquility'
    headers = {'Accept': 'application/json'}

    # do the request, but catch exceptions for connection issues
    request = request_esi(esi_url)
    result_parsed = json.loads(request)
    # catch errors

    try:
        error = result_parsed['error']
        error_code = result_parsed['code']
        resp = Response(result, status=error_code, mimetype='application/json')
        return resp
    except:
        # no error. continue.
        pass


    # parse out the corp/alliance ids and test

    try:
        alliance_id = result_parsed['alliance_id']
    except KeyError:
        alliance_id = 0

    if alliance_id > 0:
        test_result_json = str(test_alliance(sql_conn, alliance_id))
        test_result = json.loads(str(test_result_json))
        if test_result['code'] == -1:
            # shit's broken. we're done parsing.
            resp = Response(test_result_json, status=401, mimetype='application/json')
            return resp
        elif test_result['code'] == 1:
            # blue. done parsing.
            resp = Response(test_result_json, status=200, mimetype='application/json')
            return resp

    # test as a corp

    try:
        corporation_id = result_parsed['corporation_id']
    except KeyError:
        # not sure how this can happen but leaving the try anyway
        corporation_id = 'None'

    test_result_json = str(test_corp(sql_conn, baseurl, id))
    test_result = json.loads(str(test_result_json))

    if test_result['code'] == -1:
        # shit's broken. we're done parsing.
        resp = Response(test_result_json, status=401, mimetype='application/json')
        return resp
    elif test_result['code'] == 1:
        # blue. done parsing.
        resp = Response(test_result_json, status=200, mimetype='application/json')
        return resp

    # test it as an alliance
#    print('alliance test')
    test_result_json = str(test_alliance(sql_conn, id))
#    print('alliance test done')
    test_result = json.loads(str(test_result_json))

    if test_result['code'] == -1:
        # shit's broken. we're done parsing.
        resp = Response(test_result_json, status=401, mimetype='application/json')
        return resp
    elif test_result['code'] == 1:
        # blue. done parsing.
        resp = Response(test_result_json, status=200, mimetype='application/json')
        return resp

    # test it as a corp.
    # the /corporations endpoint is the least stable so we hit it last
    # see: https://github.com/ccpgames/esi-issues/issues/294

#    print('corp test')
    test_result_json = str(test_corp(sql_conn, baseurl, id))
    test_result = json.loads(str(test_result_json))
#    print('corp test done')
    if test_result['code'] == -1:
        # shit's broken. we're done parsing.
        return test_result_json
    elif test_result['code'] == 1:
        # blue. done parsing.
        return test_result_json


    # so if by this point nothing has caught it out explicitly blue, it isn't blue.

    js = json.dumps({ 'code': 0 })
    resp = Response(js, status=200, mimetype='application/json')
    return resp

def test_corp(sql_conn, baseurl, corp_id):

    # everything for testing if this is a corp and if the corp / parent
    # alliance are blue to us

    from flask import Flask, request, url_for, json, Response
    from common.request_esi import request_esi
    import requests
    import json

    # if it is a corp it is not directly in our blue table. check its alliance.

    esi_url = baseurl + 'corporations/' + str(corp_id) + '/?datasource=tranquility'
    headers = {'Accept': 'application/json'}
#    print('meow')

    # do the request, but catch exceptions for connection issues
    request = request_esi(esi_url)
    result_parsed = json.loads(request)

    # catch errors

    try:
        error = result_parsed['error']
        error_code = result_parsed['code']
        resp = Response(result, status=error_code, mimetype='application/json')
        return resp
    except:
        # no error. continue.
        pass

    try:
        alliance_id = result_parsed['alliance_id']
    except KeyError:
        # no alliance id. the test for blue on corpid was done earlier
        # so this isn't blue.
        js = json.dumps({ 'code': 0 })
        return js

    # do a final test on the derived alliance id itself

    test_result = test_alliance(sql_conn, alliance_id)
    return test_result

def test_alliance(sql_conn, alliance_id):

    from flask import Flask, request, url_for, json, Response
    from common.request_esi import request_esi
    import requests
    import json

    # check the alliance id against the blue list

    cursor = sql_conn.cursor()
    query = 'SELECT allianceID,allianceName FROM Permissions WHERE allianceID = %s'
    try:
        row = cursor.execute(query, (alliance_id,))
        cursor.close()
    except Exception as errmsg:
        js = json.dumps({ 'code': -1, 'error': 'mysql broke: ' + str(errmsg)})
        return js
    if row == 1:
        js = json.dumps({ 'code': 1 })
        return js

    # have to return a little json otherwise other stuff gets upset
    # not blue but this is not the final word
    js = json.dumps({ 'code': 0 })
    return js
