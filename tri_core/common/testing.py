def permissions(alliance_id):
    import MySQLdb as mysql
    import common.database as _database
    import common.logger as _logger

    # what can this alliance in terms of services?
    
    try:
        sql_conn = mysql.connect(
            database=_database.DB_DATABASE,
            user=_database.DB_USERNAME,
            password=_database.DB_PASSWORD,
            host=_database.DB_HOST)
        cursor = sql_conn.cursor()
    except mysql.Error as err:
        _logger.log('[' + __name__ + '] mysql error: ' + str(err), _logger.LogLevel.ERROR)
        return(False)
        
    try:
        query = 'SELECT forum, jabber, teamspeak, status FROM Permissions WHERE allianceID=%s'
        perm_count = cursor.execute(query, (alliance_id,))
        row = cursor.fetchone()
    except Exception as errmsg:
        _logger.log('[' + __name__ + '] mysql error: ' + str(errmsg), _logger.LogLevel.ERROR)
        return(False)
    finally:
        cursor.close()
        sql_conn.close()

    permissions = dict()

    if perm_count == 0: 
        _logger.log('[' + __name__ + '] permissions table for alliance {0} not found'.format(alliance_id),_logger.LogLevel.DEBUG)

        permissions['forum'] = False
        permissions['jabber'] = False
        permissions['teamspeak'] = False
        permissions['status'] = False
    else:
        _logger.log('[' + __name__ + '] permissions table for alliance {0} found'.format(alliance_id),_logger.LogLevel.DEBUG)
        forum, jabber, teamspeak, status = row
        
        permissions['forum'] = forum
        permissions['jabber'] = jabber
        permissions['teamspeak'] = teamspeak
        permissions['status'] = status
    
    return(permissions)
    
def servicetest(charid):
    # determine if a user has services successfully setup

    import ldap
    import MySQLdb as mysql
    import common.credentials.ldap as _ldap
    import common.database as _database
    import common.logger as _logger
    
    status = dict()
    _logger.log('[' + __name__ + '] determining service status of {}'.format(charid),_logger.LogLevel.DEBUG)

    try:
        sql_conn = mysql.connect(
            database=_database.DB_DATABASE,
            user=_database.DB_USERNAME,
            password=_database.DB_PASSWORD,
            host=_database.DB_HOST)
        cursor = sql_conn.cursor()
    except mysql.Error as err:
        _logger.log('[' + __name__ + '] mysql error: ' + str(err), _logger.LogLevel.ERROR)
        return(False)
    
    ldap_conn = ldap.initialize(_ldap.ldap_host, bytes_mode=False)
    try:
        ldap_conn.simple_bind_s(_ldap.admin_dn, _ldap.admin_dn_password)
    except ldap.LDAPError as error:
        _logger.log('[' + __name__ + '] LDAP connection error: {}'.format(error),_logger.LogLevel.ERROR)
        return(False, 'error')
    
    # ts3
    # need to move TS3 shit into ldap too   
    try:
        query = 'SELECT UniqueID,ClientDBID FROM Teamspeak WHERE charID=%s'
        row_count = cursor.execute(query, (charid,))
    except Exception as errmsg:
        _logger.log('[' + __name__ + '] mysql error: ' + str(errmsg), _logger.LogLevel.ERROR)
        return(False)

    if row_count == 0:
        _logger.log('[' + __name__ + '] client {} has no TS'.format(charid),_logger.LogLevel.DEBUG)
        status['ts3'] = False
    else:
        _logger.log('[' + __name__ + '] client {} has TS'.format(charid),_logger.LogLevel.DEBUG)
        status['ts3'] = True
        
    # jabber
    
    # since jabber keys directly off of the object's userPassword for authentication, if there
    # is both a pilot object and a userPassword attribute the user has jabber to some degree
    # this will include a banned user, but they are still setup in their own special way
    
    try:
        user = ldap_conn.search_s('ou=People,dc=triumvirate,dc=rocks', ldap.SCOPE_SUBTREE, filterstr='(&(objectclass=pilot)(uid={0}))'.format(charid), attrlist=['userPassword'])
        user_count = len(user)
    except ldap.LDAPError as error:
        _logger.log('[' + __name__ + '] unable to fetch ldap user: {}'.format(error),_logger.LogLevel.ERROR)
        return(False)
    if user_count == 0:
        _logger.log('[' + __name__ + '] client {} has no jabber'.format(charid),_logger.LogLevel.DEBUG)
        status['jabber'] = False
    else:
        _logger.log('[' + __name__ + '] client {} has jabber'.format(charid),_logger.LogLevel.DEBUG)
        status['jabber'] = True
        
    # forums
    
    # the forum user account creation process _always_ has a pp_main_photo column of the form 
    # https://image.eveonline.com/Character/CHARID_128.jpg with the exception of the Admin user, which
    # is not a game-based account anyway
    
    try:
        query = 'SELECT pp_main_photo FROM forum.core_members WHERE pp_main_photo=%s'
        guess = 'https://image.eveonline.com/Character/{}_128.jpg'.format(charid)
        row_count = cursor.execute(query, (guess,))
    except Exception as errmsg:
        _logger.log('[' + __name__ + '] mysql error: ' + str(errmsg), _logger.LogLevel.ERROR)
        return(False)

    if row_count == 0:
        _logger.log('[' + __name__ + '] client {} has no forums'.format(charid),_logger.LogLevel.DEBUG)
        status['forums'] = False
    else:
        _logger.log('[' + __name__ + '] client {} has TS'.format(charid),_logger.LogLevel.DEBUG)
        status['forums'] = True
    
    return(status)
    

def usertest(charid):
    # determine user status with more detail than blue or not
    
    import ldap
    import json
    import common.credentials.ldap as _ldap
    import common.logger as _logger
    import common.request_esi

    headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}
    # database connections

    ldap_conn = ldap.initialize(_ldap.ldap_host, bytes_mode=False)
    try:
        ldap_conn.simple_bind_s(_ldap.admin_dn, _ldap.admin_dn_password)
    except ldap.LDAPError as error:
        _logger.log('[' + __name__ + '] LDAP connection error: {}'.format(error),_logger.LogLevel.ERROR)
        return(False, 'error')
    
    # determine the status of the user and how to proceed
    _logger.log('[' + __name__ + '] determining status of {0}'.format(charid),_logger.LogLevel.INFO)
    
    # username

    request_url = 'https://esi.tech.ccp.is/latest/characters/{0}/?datasource=tranquility'.format(charid)
    code, result = common.request_esi.esi(__name__, request_url, 'get')

    if not code == 200:
        if code == 404:
            # 404s aren't worth logging
            pass
        else:
            # something broke severely
            _logger.log('[' + __name__ + '] /characters API error {0}: {1}'.format(code, result['error']), _logger.LogLevel.ERROR)
        return(False, 'error')

    try:
        charname = result['name']
    except KeyError as error:
        _logger.log('[' + __name__ + '] User does not exist: {0})'.format(charid), _logger.LogLevel.ERROR)
        return(False, 'error')

    # character affiliations
    # doing via requests directly so no caching the request

    
    request_url = 'https://esi.tech.ccp.is/latest/characters/affiliation/?datasource=tranquility'
    data = '[{}]'.format(charid)
    code, result = common.request_esi.esi(__name__, request_url, 'post', data)
    if not code == 200:
        _logger.log('[' + __name__ + '] unable to get character affiliations for {0}: {1}'.format(charid, error),_logger.LogLevel.ERROR)
        return(False, 'error')

    corpid = result[0]['corporation_id']
    try:
        allianceid = result[0]['alliance_id']
    except Exception as error:
        # the only way this can happen is if the character does not have an alliance.
        # unlikely but worth catching for completeness' sake
        _logger.log('[' + __name__ + '] User does not have an alliance: {0})'.format(charid), _logger.LogLevel.DEBUG)
        allianceid = 0


    # validate that the person who wants services is, in fact, blue to us
    request_url = 'https://api.triumvirate.rocks/core/isblue?id={0}'.format(charid)
    code, result = common.request_esi.esi(__name__, request_url, 'get')

    if not code == 200:
        # something broke severely
        _logger.log('[' + __name__ + '] /isblue API error {0}: {1}'.format(code, result['error']), _logger.LogLevel.ERROR)
        return(False,'error')

    isblue = result['code']
        
    # see if the user is already in the database, one way or the other.
    
    try:
        user = ldap_conn.search_s('ou=People,dc=triumvirate,dc=rocks', ldap.SCOPE_SUBTREE, filterstr='(&(objectclass=pilot)(uid={0}))'.format(charid), attrlist=['accountStatus'])
        user_count = len(user)
    except ldap.LDAPError as error:
        _logger.log('[' + __name__ + '] unable to fetch ldap user: {}'.format(error),_logger.LogLevel.ERROR)
        return(False, 'error')

    # sort out our responses to various scenarios

    if user_count == 0:
        _logger.log('[' + __name__ + '] ldap entry for {0} not found'.format(charid),_logger.LogLevel.DEBUG)
        # since the user isn't in the database, we can determine how to proceed based on blue status only
        if isblue == 0:
            _logger.log('[' + __name__ + '] charid {0} ({1}) is not blue'.format(charid,charname),_logger.LogLevel.WARNING)
            return(False, 'public')
        elif isblue == 1:
            # the user is blue and is otherwise eligible for services.
            _logger.log('[' + __name__ + '] charid {0} ({1}) is blue'.format(charid,charname),_logger.LogLevel.DEBUG)
            return(True, 'unregistered')
        else:
            _logger.log('[' + __name__ + '] isblue api error on charid {0} ({1})'.format(charid,charname),_logger.LogLevel.ERROR)
            return(False, 'error')
    else:
        _logger.log('[' + __name__ + '] ldap entry for {0} found'.format(charid),_logger.LogLevel.DEBUG)
    
    # past here, the user is validated to be in our database to some degree
    
    # account status is one of three things: 
    # public, banned, blue
    
    # always single-valued, will always be there if an ldap object exists
    status = user[0][1]['accountStatus'][0]
    status = status.decode('utf-8')

    if status == 'banned':
        # user is banned. 
        _logger.log('[' + __name__ + '] user tested to "banned"',_logger.LogLevel.INFO)
        return(False, 'banned')
    elif status == 'blue':
        # the user is already in the system, but not banned
        _logger.log('[' + __name__ + '] user tested to "blue"',_logger.LogLevel.INFO)
        return(True, 'registered')
    elif status == 'public':
        # former user. no status.
        _logger.log('[' + __name__ + '] user tested to "public"',_logger.LogLevel.INFO)
        return(False, 'public')
    else:
        # should never happen
        _logger.log('[' + __name__ + '] user tested to "wtf?"',_logger.LogLevel.INFO)
        return(False, 'error')
