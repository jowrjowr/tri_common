def audit_core():

    import common.database as _database
    import common.logger as _logger
    import MySQLdb as mysql
    import json

    import common.request_esi

    # do the needful against a given charid

    _logger.log('[' + __name__ + '] auditing CORE',_logger.LogLevel.DEBUG)

    # get all tri service users

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
    query = 'SELECT charID, charName from Users where isMain=1'
    try:
        count = cursor.execute(query)
    except Exception as err:
        _logger.log('[' + __name__ + '] mysql error: ' + str(err), _logger.LogLevel.ERROR)
        return
    _logger.log('[' + __name__ + '] number of users in core: ' + str(count), _logger.LogLevel.DEBUG)

    rows = cursor.fetchall()

    # loop and audit each one

    for row in rows:
        charid = row[0]
        charname = row[1]
        user_validate(charid, charname)
    return


def user_validate(charid, charname):

    import common.database as _database
    import common.logger as _logger
    import MySQLdb as mysql
    import json

    import common.request_esi


    # is this character blue?
    esi_url = 'http://localhost:5000/core/isblue?id=' + str(charid)

    # do the request, but catch exceptions for connection issues
    try:
        request = common.request_esi.esi(__name__, esi_url)
    except common.request_esi.NotHttp200 as error:
        if not error.code == 404:
            # something broke severely
            _logger.log('[' + __name__ + '] isblue API error ' + str(error.code) + ': ' + str(error.message), _logger.LogLevel.ERROR)
            return
        # 404 simply means this was not found as a character
        return

    result_parsed = json.loads(request)

    isblue = result_parsed['code']

    if isblue == 1:
        return
    else:
        _logger.log('[' + __name__ + '] charid {0} ({1}) is not blue'.format(charid,charname),_logger.LogLevel.WARNING)

    # remove the user from the core database

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
    query = 'DELETE FROM Users WHERE charID = %s'

    try:
        row = cursor.execute(query, (charid,))
    except Exception as errmsg:
        _logger.log('[' + __name__ + '] mysql error: ' + str(errmsg), _logger.LogLevel.ERROR)
        return
    finally:
        cursor.close()
        sql_conn.commit()
        sql_conn.close()

    _logger.log('[' + __name__ + '] CORE user {0} removed'.format(charname),_logger.LogLevel.WARNING)

    return
