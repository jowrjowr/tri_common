def audit_coregroups():

    import common.logger as _logger
    import common.database as _database
    import MySQLdb as mysql
    import json

    import common.request_esi

    _logger.log('[' + __name__ + '] auditing CORE groups',_logger.LogLevel.DEBUG)

    try:
        sql_conn = mysql.connect(
            database=_database.DB_DATABASE,
            user=_database.DB_USERNAME,
            password=_database.DB_PASSWORD,
            host=_database.DB_HOST)
    except mysql.Error as err:
        _logger.log('[' + __name__ + '] mysql error: ' + str(err), _logger.LogLevel.ERROR)
        return

    cursor = sql_conn.cursor()
    query = 'SELECT idGroups,GroupName,Members from Groups'
    try:
        cursor.execute(query)
    except Exception as err:
        _logger.log('[' + __name__ + '] mysql error: ' + str(err), _logger.LogLevel.ERROR)
        return

    rows = cursor.fetchall()
    cursor.close()
    sql_conn.close()

    # loop and audit each individual core group

    for row in rows:
        groupid = row[0]
        groupname = row[1]
        blob = row[2]
        if not blob == None:
            group_validate(groupid, groupname, blob)
    return

def group_validate(groupid, groupname, blob):

    import phpserialize
    import MySQLdb as mysql
    import json
    import copy
    import common.database as _database
    import common.logger as _logger
    import common.request_esi

    group = []
    try:
        group = phpserialize.loads(blob)
    except ValueError as err:
        pass

    newgroup = copy.deepcopy(group)
    for key in group:
        userid = int(group[key])

        # is this character blue?
        esi_url = 'http://localhost:5000/core/isblue?id=' + str(userid)

        # do the request, but catch exceptions for connection issues
        try:
            request = common.request_esi.esi(__name__, esi_url)
        except common.request_esi.NotHttp200 as error:
            if not error.code == 404:
                # something broke severely
                _logger.log('[' + __name__ + '] isblue API error ' + str(error.code) + ': ' + str(error.message), _logger.LogLevel.ERROR)
                return
            # 404 simply means this was not found as a character
            # this should never happen due to how Groups is populated
            return

        result_parsed = json.loads(request)
        isblue = result_parsed['code']
        if isblue == 0:
            _logger.log('[' + __name__ + '] removing charid {0} from group {1}'.format(userid,groupname),_logger.LogLevel.WARNING)
            newgroup.pop(key, None)


    if group == newgroup:
        # nothing to do.
        return

    serial = phpserialize.serialize(newgroup)
    # re-serialize the data stucture and push it back into the database

    try:
        sql_conn = mysql.connect(
            database=_database.DB_DATABASE,
            user=_database.DB_USERNAME,
            password=_database.DB_PASSWORD,
            host=_database.DB_HOST)
    except mysql.Error as err:
        _logger.log('[' + __name__ + '] mysql error: ' + str(err), _logger.LogLevel.ERROR)
        return

    print(groupid)
    cursor = sql_conn.cursor()
    query = 'UPDATE Groups SET Members=%s WHERE idGroups=%s'
    try:
        cursor.execute(query, (serial,groupid,))
        _logger.log('[' + __name__ + '] Group "{1}" updated'.format(userid,groupname),_logger.LogLevel.WARNING)
        sql_conn.commit()
    except Exception as err:
        _logger.log('[' + __name__ + '] mysql error: ' + str(err), _logger.LogLevel.ERROR)
        return
    finally:
        cursor.close()
        sql_conn.close()
    return
