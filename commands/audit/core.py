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

    dn = 'ou=People,dc=triumvirate,dc=rocks'
    filterstr = '(&(!(accountstatus=banned))(!(accountStatus=immortal)))'
    attributes = ['uid', 'characterName', 'accountStatus', 'authGroup', 'corporation', 'alliance' ]
    code, users = _ldaphelpers.ldap_search(__name__, dn, filterstr, attributes)

    if code == False:
        return
    else:
        result_count = len(users)

    _logger.log('[' + __name__ + '] total non-banned ldap users: {}'.format(result_count),_logger.LogLevel.DEBUG)

    # bulk affiliations fetch

    data = []
    chunksize = 750 # current ESI max is 1000 but we'll be safe
    for user in users.keys():
        try:
            charid = int( users[user]['uid'] )
            data.append(charid)
        except Exception as error:
            pass
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

            # locate the dn from the charid
            charid = item['character_id']
            for user in users.keys():
                try:
                    ldap_charid = int( users[user]['uid'] )
                except Exception as error:
                    ldap_charid = None

                if ldap_charid == charid:
                    #print('matched dn {0} to uid {1} ldap charid {2}'.format(user, charid, ldap_charid))
                    dn = user

            users[dn]['esi_corp'] = item['corporation_id']
            if 'alliance_id' in item.keys():
                users[dn]['esi_alliance'] = item['alliance_id']
            else:
                users[dn]['esi_alliance'] = None

    # groups that a non-blue user is allowed to have

    safegroups = set([ 'public', 'ban_pending' ])

    # loop through each user and determine the correct status

    for user in users.keys():
        dn = user

        if users[user]['uid'] == None:
            continue

        charid = int(users[user]['uid'])
        status = users[user]['accountStatus']
        charname = users[user]['characterName']
        groups = users[user]['authGroup']

        # bad data protection
        try:
            esi_allianceid = users[user]['esi_alliance']
        except:
            esi_allianceid = None
        try:
            ldap_allianceid = int(users[user]['alliance'])
        except:
            ldap_allianceid = None
        try:
            esi_corpid = users[user]['esi_corp']
        except:
            esi_corpid = None
        try:
            ldap_corpid = int(users[user]['corporation'])
        except:
            ldap_corpid = None
        # user's effective managable groups
        groups = list( set(groups) - safegroups )

        # tinker with ldap to account for reality

        if not esi_allianceid == ldap_allianceid:
            # update a changed alliance id
            _ldaphelpers.update_singlevalue(dn, 'alliance', str(esi_allianceid))
        if not esi_corpid == ldap_corpid:
            # update a changed corp id
            _ldaphelpers.update_singlevalue(dn, 'corporation', str(esi_corpid))

        if status == 'blue':
            # blue in ldap

            if not esi_allianceid in vanguard:
                # need to adjust to public
                _ldaphelpers.update_status(dn, 'public')
                _ldaphelpers.update_singlevalue(dn, 'accountStatus', 'public')

            # give them the correct base authgroups

            if esi_allianceid == triumvirate and 'triumvirate' not in groups:
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
            if esi_allianceid in vanguard:
                # oops. time to fix you.
                _ldaphelpers.update_singlevalue(dn, 'accountStatus', 'blue')

