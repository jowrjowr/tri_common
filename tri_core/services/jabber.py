def setup(charid, clobber):

    import common.credentials.jabber as _jabber
    import common.logger as _logger
    import common.database as _database
    import uuid
    import json
    import requests
    import MySQLdb as mysql

    # setup the jabber service for a user

    _logger.log('[' + __name__ + '] configuring jabber service for {0}'.format(charid),_logger.LogLevel.INFO)

    jabber_baseurl = 'http://localhost:9090/plugins/restapi/v1/'
    headers = {'Accept': 'application/json', 'Authorization': _jabber.atoken, 'Content-Type': 'application/json' }

    try:
        sql_conn = mysql.connect(
            database=_database.DB_DATABASE,
            user=_database.DB_USERNAME,
            password=_database.DB_PASSWORD,
            host=_database.DB_HOST)
        cursor = sql_conn.cursor()
    except mysql.Error as err:
        _logger.log('[' + __name__ + '] mysql error: ' + str(err), _logger.LogLevel.ERROR)
        return False

    # get relevant information about the user

    # get character affiliations
    # doing via requests directly so no caching the request

    esi_headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}
    request_url = 'https://esi.tech.ccp.is/latest/characters/affiliation/?datasource=tranquility'
    data = '[{}]'.format(charid)
    result = requests.post(request_url, headers=esi_headers, data=data)

    try:
        result.raise_for_status()
    except requests.exceptions.HTTPError as error:
        _logger.log('[' + __name__ + '] unable to get character affiliations for {0}: {1}'.format(charid, error),_logger.LogLevel.ERROR)
        return False

    result = json.loads(result.text)
    corpid = result[0]['corporation_id']
    allianceid = result[0]['alliance_id']

    # get database stored info

    query = 'SELECT ServiceUsername,ServicePassword FROM Users WHERE charID = %s'
    try:
        cursor.execute(query, (charid,))
        serviceuser, servicepass = cursor.fetchone()
    except mysql.Error as err:
        _logger.log('[' + __name__ + '] mysql error: ' + str(err), _logger.LogLevel.ERROR)
        return False

    # test if the user exists. if it does, we remove it.
    # unless we don't want to.

    try:
        request_url = jabber_baseurl + 'users/' + serviceuser
        request = requests.get(request_url, headers=headers, timeout=5)
    except Exception as err:
        _logger.log('[' + __name__ + '] jabber api call failed: {0}'.format(err),_logger.LogLevel.DEBUG)
        return False

    if request.status_code == 404:
        exists = False
        _logger.log('[' + __name__ + '] jabber user {0} does not exist'.format(serviceuser),_logger.LogLevel.DEBUG)
    elif request.status_code == 200:
        exists = True
        _logger.log('[' + __name__ + '] clobbering pre-existing jabber user {0}'.format(serviceuser),_logger.LogLevel.WARNING)
    else:
        _logger.log('[' + __name__ + '] unable to check existence of user {0}'.format(serviceuser),_logger.LogLevel.ERROR)
        return False

    if exists == True and clobber == False:
        _logger.log('[' + __name__ + '] user {0} already exists, but clobber == false'.format(serviceuser),_logger.LogLevel.ERROR)
        return False

    # remove the existing user
    # this will leave a logged-in user online but i don't care enough to deal with a lockout

    if exists == True:
        try:
            request_url = jabber_baseurl + 'users/' + serviceuser
            request = requests.delete(request_url, headers=headers, timeout=5)
        except Exception as err:
            _logger.log('[' + __name__ + '] jabber api call failed: {0}'.format(err),_logger.LogLevel.DEBUG)
            return False
        if request.status_code == 404:
            _logger.log('[' + __name__ + '] jabber user {0} does not exist'.format(serviceuser),_logger.LogLevel.DEBUG)
        elif request.status_code == 200:
            _logger.log('[' + __name__ + '] jabber user {0} removed'.format(serviceuser),_logger.LogLevel.WARNING)
        else:
            _logger.log('[' + __name__ + '] unable to delete user {0}'.format(serviceuser),_logger.LogLevel.ERROR)
            return False

    # create the new user

    try:
        data = {"username": serviceuser, "password": servicepass}
        request_url = jabber_baseurl + 'users'
        request = requests.post(request_url, headers=headers, timeout=5, data=data)
    except Exception as err:
        _logger.log('[' + __name__ + '] jabber api call failed: {0}'.format(err),_logger.LogLevel.DEBUG)
        return False

    if request.status_code == 201:
        _logger.log('[' + __name__ + '] jabber user {0} created'.format(serviceuser),_logger.LogLevel.WARNING)
    else:
        print(headers)
        print(request_url)
        print(data)
        print(request.headers)
        print(request.status_code)
        _logger.log('[' + __name__ + '] unable to create user {0}'.format(serviceuser),_logger.LogLevel.ERROR)
        return False

    return True
