import asyncio

def audit_jabber():

    import common.credentials.jabber as _jabber
    import common.logger as _logger

    import logging
    import requests
    import json

    _logger.log('[' + __name__ + '] auditing jabber',_logger.LogLevel.DEBUG)

    # get all jabber users
    headers = {'Accept': 'application/json', 'Content-Type': 'application/json', 'Authorization': str(_jabber.atoken)}

    # hardcode service user for testing
    jabber_url = _jabber.baseurl + 'users/'

    try:
        request = requests.get(jabber_url, headers=headers, timeout=10)
    except Exception as err:
        pass

    if request.status_code == 404:
        _logger.log('[' + __name__ + '] jabber /users endpoint does not exist?!',_logger.LogLevel.WARNING)

    if request.status_code != 200 and request.status_code != 404:
        # errors that aren't "not found":
        # hard fail on breakage? not sure.
        _logger.log('[' + __name__ + '] Unable to access /users endpoint',_logger.LogLevel.WARNING)
        return

    result_parsed = json.loads(request.text)

    loop = asyncio.new_event_loop()
    for user in result_parsed['user']:
        serviceuser = user['username']
        _logger.log('[' + __name__ + '] Validating user {0}'.format(serviceuser),_logger.LogLevel.DEBUG)

        # two current exceptions as they are not 'real users': admin and sovereign

        if serviceuser == 'admin':
            pass
        elif serviceuser == 'sovereign':
            pass
        else:
            # otherwise:
            loop.run_until_complete(user_validate(serviceuser))
    loop.close()
    return

async def user_validate(serviceuser):

    import MySQLdb as mysql
    import common.database as _database
    import common.credentials.jabber as _jabber
    import common.logger as _logger
    import common.request_esi

    import logging
    import requests
    import json

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
    query = 'SELECT ServiceUsername FROM Users WHERE ServiceUsername = %s'

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

    # a nonzero return means the jabber user is linked to an active core user

    if row == 1:
        # we're done.
        #_logger.log('[' + __name__ + '] ...user {0} valid'.format(serviceuser),_logger.LogLevel.DEBUG)
        return

    # oops orphan. we hate orphans.

    _logger.log('[' + __name__ + '] Orphan jabber user: {0}'.format(serviceuser), _logger.LogLevel.WARNING)

    # remove the orphan user

    logging.getLogger("requests").setLevel(logging.WARNING)
    headers = {'Accept': 'application/json', 'Content-Type': 'application/json', 'Authorization': str(_jabber.atoken)}

    jabber_url = _jabber.baseurl + 'users/' + serviceuser

    try:
        request = requests.delete(jabber_url, headers=headers, timeout=10)
    except Exception as err:
        pass

    if request.status_code == 404:
        _logger.log('[' + __name__ + '] jabber user {0} does not exist?!'.format(serviceuser),_logger.LogLevel.WARNING)

    if request.status_code != 200 and request.status_code != 404:
        # errors that aren't "not found":
        # hard fail on breakage? not sure.
        _logger.log('[' + __name__ + '] Unable to delete jabber user {0}'.format(serviceuser),_logger.LogLevel.WARNING)
        return

    _logger.log('[' + __name__ + '] Jabber user {0} removed'.format(serviceuser),_logger.LogLevel.WARNING)

    return
