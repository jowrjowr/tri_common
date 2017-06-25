def audit_core():

    import json
    import common.request_esi
    import common.logger as _logger
    import common.database as _database
    import common.credentials.ldap as _ldap
    import ldap
    import ldap.modlist
    import math
    import MySQLdb as mysql
    from common.api import base_url

    # keep the ldap account status entries in sync

    _logger.log('[' + __name__ + '] auditing CORE LDAP',_logger.LogLevel.INFO)

    # connections

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

    ldap_conn = ldap.initialize(_ldap.ldap_host, bytes_mode=False)
    try:
        ldap_conn.simple_bind_s(_ldap.admin_dn, _ldap.admin_dn_password)
    except ldap.LDAPError as error:
        _logger.log('[' + __name__ + '] LDAP connection error: {}'.format(error),_logger.LogLevel.ERROR)

    # fetch vanguard alliances
    cursor = sql_conn.cursor()
    query = 'SELECT allianceID FROM Permissions'
    try:
        cursor.execute(query)
        rows = cursor.fetchall()
    except mysql.Error as err:
        _logger.log('[' + __name__ + '] mysql error: ' + str(err), _logger.LogLevel.ERROR)
        return False
    finally:
        cursor.close()
        sql_conn.close()

    vanguard = []
    for row in rows:
        vanguard.append(row[0])

    # fetch all non-banned LDAP users
    try:
        result = ldap_conn.search_s('ou=People,dc=triumvirate,dc=rocks',
            ldap.SCOPE_SUBTREE,
            filterstr='(&(!(accountstatus=banned))(!(accountStatus=immortal)))',
            attrlist=['uid', 'characterName', 'accountStatus' ]
        )
        user_count = result.__len__()
    except ldap.LDAPError as error:
        _logger.log('[' + __name__ + '] unable to fetch ldap users: {}'.format(error),_logger.LogLevel.ERROR)

    _logger.log('[' + __name__ + '] total non-banned ldap users: {}'.format(user_count),_logger.LogLevel.DEBUG)

    # get a list of uids for us to check affiliations with
    users = dict()
    for user in result:
        dn, info = user

        if dn == 'ou=People,dc=triumvirate,dc=rocks':
            continue
        charname = info['characterName'][0].decode('utf-8')
        charid = info['uid'][0].decode('utf-8')
        status = info['accountStatus'][0].decode('utf-8')
        charid = int(charid)

        users[charid] = dict()
        users[charid]['charname'] = charname
        users[charid]['dn'] = dn
        users[charid]['status'] = status

    # bulk affiliations fetch

    data = []
    chunksize = 750 # current ESI max is 1000 but we'll be safe
    for charid in users.keys():
        data.append(charid)
    length = len(data)
    chunks = math.ceil(length / chunksize)
    for i in range(0, chunks):
        chunk = data[:chunksize]
        del data[:chunksize]
        _logger.log('[' + __name__ + '] passing {0} items to affiliations endpoint'.format(len(chunk)), _logger.LogLevel.INFO)
        request_url = base_url + 'characters/affiliation/?datasource=tranquility'
        chunk = json.dumps(chunk)
        code, result = common.request_esi.esi(__name__, request_url, method='post', data=chunk)
        for item in result:
            charid = item['character_id']
            users[charid]['corpid'] = item['corporation_id']
            if 'alliance_id' in item.keys():
                users[charid]['allianceid'] = item['alliance_id']
            else:
                users[charid]['allianceid'] = None

    # loop through each user and determine the correct status

    for charid in users.keys():
        status = users[charid]['status']
        charname = users[charid]['charname']
        dn = users[charid]['dn']

        try:
            allianceid = users[charid]['allianceid']
        except Exception as error:
            allianceid = None

        if status == 'blue' and not allianceid in vanguard:
            # need to adjust to public
            update_status(dn, 'public')

        if not status == 'blue' and allianceid in vanguard:
            # need to adjust to blue
            update_status(dn, 'blue')

def update_status(dn, status):
    import common.logger as _logger
    import common.credentials.ldap as _ldap
    import json
    import ldap
    import ldap.modlist

    # update the user's status to whatever

    ldap_conn = ldap.initialize(_ldap.ldap_host, bytes_mode=False)
    try:
        ldap_conn.simple_bind_s(_ldap.admin_dn, _ldap.admin_dn_password)
    except ldap.LDAPError as error:
        _logger.log('[' + __name__ + '] LDAP connection error: {}'.format(error),_logger.LogLevel.ERROR)

    mod_attrs = [ (ldap.MOD_REPLACE, 'accountStatus', status.encode('utf-8') ) ]

    try:
        result = ldap_conn.modify_s(dn, mod_attrs)
    except ldap.LDAPError as error:
        _logger.log('[' + __name__ + '] unable to update dn {0} accountStatus: {1}'.format(dn,error),_logger.LogLevel.ERROR)
    _logger.log('[' + __name__ + '] dn {0} accountStatus set to {1}'.format(dn, status),_logger.LogLevel.INFO)
