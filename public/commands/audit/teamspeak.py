def audit_teamspeak():

    import common.database as _database
    import common.jabber as _jabber
    import common.ts3 as _ts3
    import common.logger as _logger

    import logging
    import requests
    import json
    import ts3

    import common.request_esi

    _logger.log('[' + __name__ + '] auditing teamspeak',_logger.LogLevel.DEBUG)
    logging.getLogger("requests").setLevel(logging.WARNING)

    # http://py-ts3.readthedocs.io/en/latest/

    try:
        # Note, that the client will wait for the response and raise a
        # **TS3QueryError** if the error id of the response is not 0.
        ts3conn = ts3.query.TS3Connection(_ts3.TS_HOST)
        ts3conn.login(
            client_login_name=_ts3.TS_USER,
            client_login_password=_ts3.TS_PASSWORD
        )
    except ts3.query.TS3QueryError as err:
        _logger.log('[' + __name__ + '] unable to connect to TS3: {0}'.format(err.resp.error["msg"]),_logger.LogLevel.ERROR)
        return


    ts3conn.use(sid=_ts3.TS_SERVER_ID)

    # ts3 errorhandling is goofy.
    # if it can't find the user, it raises an error so we'll just assume failure means no user
    # and continue

    try:
        resp = ts3conn.clientdblist()
        ts3conn.quit()
    except ts3.query.TS3QueryError as err:
        _logger.log('[' + __name__ + '] ts3 error: {0}'.format(err),_logger.LogLevel.WARNING)

    for user in resp.parsed:
        serviceuser = user['client_nickname']
        _logger.log('[' + __name__ + '] Validating ts3 user {0}'.format(serviceuser),_logger.LogLevel.DEBUG)

        # not really proper clients, so don't do anything

        if serviceuser == 'ServerQuery Guest':
            pass
        elif serviceuser == 'sovereign':
            pass
        else:
            # otherwise:
            user_validate(user)

    return ''

def user_validate(user):

    import MySQLdb as mysql
    import common.database as _database
    import common.ts3 as _ts3
    import common.logger as _logger

    import logging
    import requests
    import json
    import time
    import ts3

    try:
        sql_conn = mysql.connect(
            database=_database.DB_DATABASE,
            user=_database.DB_USERNAME,
            password=_database.DB_PASSWORD,
            host=_database.DB_HOST)
    except mysql.Error as err:
        _logger.log('[' + __name__ + '] mysql error: ' + str(err), _logger.LogLevel.ERROR)
        return

    serviceuser = user['client_nickname']
    ts3_id = user['cldbid']

    cursor = sql_conn.cursor()
    query = 'SELECT ServiceUsername FROM Users WHERE charName = %s'

    try:
        row = cursor.execute(query, (serviceuser,))
    except Exception as errmsg:
        _logger.log('[' + __name__ + '] mysql error: ' + str(errmsg), _logger.LogLevel.ERROR)
        js = json.dumps({ 'code': -1, 'error': 'mysql broke: ' + str(errmsg)})
        resp = Response(js, status=401, mimetype='application/json')
        return resp
    finally:
        cursor.close()
        sql_conn.commit()
        sql_conn.close()

    # a nonzero return means the ts3 user is linked to an active core user

    if row == 1:
        # we're done.
        _logger.log('[' + __name__ + '] ...user {0} valid'.format(serviceuser),_logger.LogLevel.DEBUG)
        return

    # oops orphan. we hate orphans.
    # log the everloving shit out of this

    lastconnected = time.gmtime(int(user['client_lastconnected']))
    lastconnected_iso = time.strftime("%Y-%m-%dT%H:%M:%S", lastconnected)
    created = time.gmtime(int(user['client_created']))
    created_iso = time.strftime("%Y-%m-%dT%H:%M:%S", created)
    _logger.log('[' + __name__ + '] Orphan ts3 user: {0}'.format(serviceuser), _logger.LogLevel.WARNING)
    _logger.log('[' + __name__ + '] User {0} created: {1}, last login: {2}, last ip: {3}, total connections: {4}'.format(
            serviceuser,created_iso,lastconnected_iso,
            user['client_lastip'],user['client_totalconnections']
        ), _logger.LogLevel.WARNING)

    # remove orphan ts3 users


    try:
        # Note, that the client will wait for the response and raise a
        # **TS3QueryError** if the error id of the response is not 0.
        ts3conn = ts3.query.TS3Connection(_ts3.TS_HOST)
        ts3conn.login(
            client_login_name=_ts3.TS_USER,
            client_login_password=_ts3.TS_PASSWORD
        )
    except ts3.query.TS3QueryError as err:
        _logger.log('[' + __name__ + '] unable to connect to TS3: {0}'.format(err.resp.error["msg"]),_logger.LogLevel.ERROR)
        return

    ts3conn.use(sid=_ts3.TS_SERVER_ID)

    try:
        resp = ts3conn.clientdbdelete(cldbid=ts3_id)
        _logger.log('[' + __name__ + '] ts3 user {0} removed'.format(serviceuser),_logger.LogLevel.WARNING)
    except ts3.query.TS3QueryError as err:
        _logger.log('[' + __name__ + '] ts3 error: {0}'.format(err),_logger.LogLevel.WARNING)

    # client removed. gg.

    return
