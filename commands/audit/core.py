def audit_core():

    import json
    import common.request_esi
    import common.logger as _logger
    import common.database as _database
    import common.credentials.ldap as _ldap
    import common.ldaphelpers as _ldaphelpers
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

    # vanguard alliance ids
    triumvirate = 933731581
    vanguard = []
    for row in rows:
        vanguard.append(row[0])

    # fetch all non-banned LDAP users
    try:
        result = ldap_conn.search_s('ou=People,dc=triumvirate,dc=rocks',
            ldap.SCOPE_SUBTREE,
            filterstr='(&(!(accountstatus=banned))(!(accountStatus=immortal)))',
            attrlist=['uid', 'characterName', 'accountStatus', 'authGroup', 'corporation', 'alliance' ]
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

        charid = int( info['uid'][0].decode('utf-8') )

        try:
            corpid = int( info['corporation'][0].decode('utf-8') )
        except Exception as error:
            corpid = None

        try:
            allianceid = int( info['alliance'][0].decode('utf-8') )
        except Exception as error:
            allianceid = None

        status = info['accountStatus'][0].decode('utf-8')
        groups = list(map(lambda x: x.decode('utf-8'), info['authGroup']))

        users[charid] = dict()
        users[charid]['charname'] = charname
        users[charid]['dn'] = dn
        users[charid]['status'] = status
        users[charid]['groups'] = groups
        users[charid]['ldap_corpid'] = corpid
        users[charid]['ldap_allianceid'] = allianceid

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

    # groups that a non-blue user is allowed to have

    safegroups = { 'public', 'ban_pending' }

    # loop through each user and determine the correct status

    for charid in users.keys():
        status = users[charid]['status']
        charname = users[charid]['charname']
        dn = users[charid]['dn']
        groups = users[charid]['groups']
        # user's effective managable groups
        groups = list( set(groups) - safegroups )

        # faulty data protections galore
        try:
            ldap_allianceid = users[charid]['ldap_allianceid']
        except Exception as error:
            ldap_allianceid = None

        try:
            allianceid = users[charid]['allianceid']
        except Exception as error:
            allianceid = None

        try:
            ldap_corpid = users[charid]['ldap_corpid']
        except Exception as error:
            ldap_corpid = None

        # tinker with ldap to account for reality

        if not allianceid == ldap_allianceid:
            # update a changed alliance id
            update_singlevalue(dn, 'alliance', str(allianceid))
        if not corpid == ldap_corpid:
            # update a changed corp id
            update_singlevalue(dn, 'corporation', str(corpid))

        if status == 'blue':
            # blue in ldap

            if not allianceid in vanguard:
                # need to adjust to public
                _ldaphelpers.update_status(dn, 'public')
                _ldaphelpers.update_singlevalue(dn, 'accountStatus', 'public')

            # give them the correct base authgroups

            if allianceid == triumvirate and 'triumvirate' not in groups:
                # all tri get trimvirate
                _ldaphelpers.add_value(dn, 'authGroup', 'triumvirate')

            if 'vanguard' not in groups:
                # all blue get vanguard
                _ldaphelpers.add_value(dn, 'authGroup', 'vanguard')

        else:
            # not blue in ldap, obv
            if len(groups) > 0:
                # purge groups off someone who has more than they should
                # not a security issue per se, but keeps the management tools clean
                _ldaphelpers.purge_authgroups(dn, groups)
            if allianceid in vanguard:
                # oops. time to fix you.
                _ldaphelpers.update_singlevalue(dn, 'accountStatus', 'blue')

