def registeruser(charid, atoken, rtoken, isalt, altof):
    # put the barest skeleton of information into ldap/mysql

    import common.logger as _logger
    import common.credentials.database as _database
    import tri_core.common.testing as _testing
    import common.credentials.ldap as _ldap
    import common.request_esi
    from common.graphite import sendmetric
    from common.api import base_url
    import ldap
    import MySQLdb as mysql

    import json
    import datetime
    import uuid
    import time

    from datetime import datetime
    from passlib.hash import ldap_salted_sha1

    # get character affiliations

    headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}

    if isalt == False:
        _logger.log('[' + __name__ + '] registering user {}'.format(charid),_logger.LogLevel.INFO)
    else:
        _logger.log('[' + __name__ + '] registering user {0} (alt of {1})'.format(charid, altof),_logger.LogLevel.INFO)

    try:
        sql_conn = mysql.connect(
            database=_database.DB_DATABASE,
            user=_database.DB_USERNAME,
            password=_database.DB_PASSWORD,
            host=_database.DB_HOST)
        cursor = sql_conn.cursor()
    except mysql.Error as err:
        _logger.log('[' + __name__ + '] mysql error: ' + str(err), _logger.LogLevel.ERROR)
        return(False, 'error')

    ldap_conn = ldap.initialize(_ldap.ldap_host, bytes_mode=False)
    try:
        ldap_conn.simple_bind_s(_ldap.admin_dn, _ldap.admin_dn_password)
    except ldap.LDAPError as error:
        _logger.log('[' + __name__ + '] LDAP connection error: {}'.format(error),_logger.LogLevel.ERROR)
        return(False, 'error')

    # character affiliations
    request_url = base_url + 'characters/affiliation/?datasource=tranquility'
    data = '[{}]'.format(charid)
    code, result = common.request_esi.esi(__name__, request_url, method='post', data=data)
    if not code == 200:
        _logger.log('[' + __name__ + '] unable to get character affiliations for {0}: {1}'.format(charid, error),_logger.LogLevel.ERROR)
        return(False, 'error')

    _logger.log('[' + __name__ + '] character affiliations output for {0}: {1}'.format(charid, json.dumps(result)),_logger.LogLevel.DEBUG)
    corpid = result[0]['corporation_id']
    allianceid = result[0]['alliance_id']

    # username
    request_url = base_url + 'characters/{0}/?datasource=tranquility'.format(charid)

    code, result = common.request_esi.esi(__name__, request_url, 'get')
    _logger.log('[' + __name__ + '] character output for {0}: {1}'.format(charid, json.dumps(result)),_logger.LogLevel.DEBUG)

    if not code == 200:
        _logger.log('[' + __name__ + '] /characters API error {0}: {1}'.format(code, result['error']), _logger.LogLevel.ERROR)
        return(False, 'error')

    try:
        charname = result['name']
    except KeyError as error:
        _logger.log('[' + __name__ + '] User does not exist: {0})'.format(charid), _logger.LogLevel.ERROR)
        return(False, 'error')

    # get corp name
    request_url = base_url + "corporations/" + str(corpid) + '/?datasource=tranquility'

    code, result = common.request_esi.esi(__name__, request_url, 'get')
    _logger.log('[' + __name__ + '] corporations output for {0}: {1}'.format(corpid, json.dumps(result)),_logger.LogLevel.DEBUG)

    if not code == 200:
        _logger.log('[' + __name__ + '] /corporations API error {0} for corp id {1}: {2}'.format(code, corpid, result['error']), _logger.LogLevel.ERROR)
        return('SORRY, INTERNAL API ERROR')

    try:
        corpname = result['corporation_name']
    except Exception as error:
        _logger.log('[' + __name__ + '] /corporations API did not return corp name for corpid {0}: {1}'.format(corpid, error), _logger.LogLevel.ERROR)
        return('SORRY, ESI API ERROR')

    # get alliance name
    request_url = base_url + "alliances/" + str(allianceid) + '/?datasource=tranquility'

    code, result = common.request_esi.esi(__name__, request_url, 'get')

    if not code == 200:
        _logger.log('[' + __name__ + '] /alliances API error {0}: {1}'.format(code, result['error']), _logger.LogLevel.ERROR)
        return('SORRY, ESI API ERROR')

    alliancename = result['alliance_name']

    # setup the service user/pass

    serviceuser = charname
    serviceuser = serviceuser.replace(" ", '')
    serviceuser = serviceuser.replace("'", '')
    servicepass = uuid.uuid4().hex[:8]

    # store user data in users table
    query =  'REPLACE INTO Users (charID, charName, corpID, corpName, allianceID, allianceName, ServiceUsername, ServicePassword, isMain, isAlt)'
    query += 'VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)'

    try:
        row = cursor.execute(
            query, (
                charid,
                charname,
                corpid,
                corpname,
                allianceid,
                alliancename,
                serviceuser,
                servicepass,
                1,
                0,
            ),
        )
        _logger.log('[' + __name__ + '] user {0} user data registered (mysql)'.format(charid), _logger.LogLevel.INFO)
    except Exception as errmsg:
        _logger.log('[' + __name__ + '] mysql error: ' + str(errmsg), _logger.LogLevel.ERROR)
        return(False, 'error')
    finally:
        # done with mysql
        cursor.close()
        sql_conn.commit()
        sql_conn.close()

    # store in LDAP

    cn = charname.replace(" ", '')
    cn = cn.replace("'", '')
    cn = cn.lower()
    dn = "cn={},ou=People,dc=triumvirate,dc=rocks".format(cn)
    # build a random password until one is 
    password = uuid.uuid4().hex
    password_hash = ldap_salted_sha1.hash(password)

    user = dict()
    user['cn'] = cn
    user['charid'] = charid
    user['charname'] = charname
    user['accountstatus'] = 'blue'
    user['corpid'] = corpid
    user['allianceid'] = allianceid
    user['atoken'] = atoken
    user['rtoken'] = rtoken
    user['password_hash'] = password_hash

    # alt storage
    if isalt == True:
        user['altof'] = altof

    # sort out basic auth groups

    authgroups = ['public', 'vanguard'] # default level of access for blues
    if 'allianceid' in user.keys():
        if user['allianceid'] == 933731581:
            # tri specific authgroup
            authgroups.append('triumvirate')

    user['authgroup'] = authgroups
    # encode to make ldap happy
    for item in user.keys():
        # everything but authgroup is a single valued entry that needs to be encoded
        if not item == 'authgroup':
            user[item] = str(user[item]).encode('utf-8')
        else:
            newgroups = []
            for group in authgroups:
                group = str(group).encode('utf-8')
                newgroups.append(group)
            user['authgroup'] = newgroups

    # build the ldap object
    attrs = []
    attrs.append(('objectClass', ['top'.encode('utf-8'), 'pilot'.encode('utf-8'), 'simpleSecurityObject'.encode('utf-8'), 'organizationalPerson'.encode('utf-8')]))
    attrs.append(('sn', [user['cn']]))
    attrs.append(('cn', [user['cn']]))
    attrs.append(('uid', [user['charid']]))
    attrs.append(('characterName', [user['charname']]))
    attrs.append(('accountStatus', [user['accountstatus']]))
    attrs.append(('authGroup', user['authgroup']))
    attrs.append(('corporation', [user['corpid']]))
    attrs.append(('alliance', [user['allianceid']]))
    attrs.append(('esiAccessToken', [user['atoken']]))
    attrs.append(('esiRefreshToken', [user['rtoken']]))
    attrs.append(('userPassword', [user['password_hash']]))

    if isalt == True:
        attrs.append(('altOf', [user['altof']]))

    # build out the modification in case
    mod_attrs = []
    for attr in attrs:
        attribute = (ldap.MOD_REPLACE,) + attr
        mod_attrs.append(attribute)

    # check if it exists
    # ldap doesn't really have a replace into like mysql...

    try:
        # search specifically for users with a defined uid (everyone, tbh) and a defined refresh token (not everyone)
        result = ldap_conn.search_s(
            'ou=People,dc=triumvirate,dc=rocks',
            ldap.SCOPE_SUBTREE,
            filterstr='(uid={})'.format(charid),
        )
        record_count = result.__len__()
    except ldap.LDAPError as error:
        _logger.log('[' + __name__ + '] unable to fetch ldap information for {0}: {1}'.format(charid, error),_logger.LogLevel.ERROR)
        return(False, 'error')

    if record_count == 0:
        try:
            result = ldap_conn.add_s(dn, attrs)
        except Exception as e:
            _logger.log('[' + __name__ + '] unable to register user {0} in ldap: {1}'.format(charid, e), _logger.LogLevel.ERROR)
            return(False, 'error')
    else:
        try:
            result = ldap_conn.modify_s(dn, mod_attrs)
        except Exception as e:
            _logger.log('[' + __name__ + '] unable to update existing user {0} in ldap: {1}'.format(charid, e), _logger.LogLevel.ERROR)
            return(False, 'error')

    if isalt == True:
        _logger.log('[' + __name__ + '] new user {0} ({1}) (alt of {2}) registered (ldap)'.format(charid, charname, altof), _logger.LogLevel.INFO)
    else:
        _logger.log('[' + __name__ + '] new user {0} ({1}) registered (ldap)'.format(charid, charname), _logger.LogLevel.INFO)

    return(True, 'success')

