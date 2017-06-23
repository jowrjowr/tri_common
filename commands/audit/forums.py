def audit_forums():

    import common.request_forums as _forums
    import common.logger as _logger
    import common.credentials.ldap as _ldap
    import common.credentials.database as _database
    import common.credentials.forums as _forumcreds
    import common.request_esi
    from common.api import base_url
    from common.graphite import sendmetric
    from collections import defaultdict
    import ldap
    import json
    import urllib
    import html
    import MySQLdb as mysql
    _logger.log('[' + __name__ + '] auditing forums',_logger.LogLevel.INFO)

    # setup connections

    ldap_conn = ldap.initialize(_ldap.ldap_host, bytes_mode=False)
    try:
        ldap_conn.simple_bind_s(_ldap.admin_dn, _ldap.admin_dn_password)
    except ldap.LDAPError as error:
        _logger.log('[' + __name__ + '] LDAP connection error: {}'.format(error),_logger.LogLevel.ERROR)
        return False

    try:
        sql_conn_core = mysql.connect(
            database=_database.DB_DATABASE,
            user=_database.DB_USERNAME,
            password=_database.DB_PASSWORD,
            host=_database.DB_HOST)
    except mysql.Error as err:
        _logger.log('[' + __name__ + '] mysql error: ' + str(err), _logger.LogLevel.ERROR)
        return False

    try:
        sql_conn = mysql.connect(
            database=_forumcreds.mysql_db,
            user=_forumcreds.mysql_user,
            password=_forumcreds.mysql_pass,
            host=_forumcreds.mysql_host)
    except mysql.Error as err:
        _logger.log('[' + __name__ + '] mysql error: ' + str(err), _logger.LogLevel.ERROR)
        return False

    # get everything from the permissions table

    cursor = sql_conn_core.cursor()
    query = 'SELECT allianceID,forum FROM Permissions'
    forum_mappings = dict()

    try:
        cursor.execute(query)
        rows = cursor.fetchall()
    except mysql.Error as err:
        _logger.log('[' + __name__ + '] mysql error: ' + str(err), _logger.LogLevel.ERROR)
        return False
    finally:
        cursor.close()
        sql_conn_core.close()

    # this maps the alliance id to the primary forum group

    for row in rows:
        forum_mappings[row[0]] = row[1]

    # get all the forum users and stuff them into a dict for later processing

    page = 1
    total_pages = 2
    orphan = 0

    users = dict()

    while (page < total_pages):

        code, response = _forums.forums(__name__, '/core/members&page={0}'.format(page), 'get')
        _logger.log('[' + __name__ + '] /core/members output (page {0}): {1}'.format(page, response),_logger.LogLevel.DEBUG)

        if not code == 200:
            _logger.log('[' + __name__ + '] /core/members API error {0} (page {1}): {2}'.format(code, page, response), _logger.LogLevel.ERROR)
            return False
        response = json.loads(response)

        if page == 1:

            # establish page count ONCE
            total_pages = response['totalPages']

            # some metric logging
            total_users = response['totalResults']
            _logger.log('[' + __name__ + '] forum users: {0}'.format(total_users), _logger.LogLevel.INFO)
            sendmetric(__name__, 'forums', 'statistics', 'total_users', total_users)

        for item in response['results']:

            charname = html.unescape(item['formattedName'])
            users[charname] = dict()
            users[charname]['charname'] = charname
            users[charname]['doomheim'] = False
            # the ids are internal forum group ids
            users[charname]['id'] = item['id']
            users[charname]['primary'] = dict()
            users[charname]['primary'][item['primaryGroup']['id']] = item['primaryGroup']['formattedName']
            users[charname]['secondary'] = dict()

            secondarygroups = dict()

            for group in item['secondaryGroups']:
                secondarygroups[group['id']] = group['formattedName']

            users[charname]['secondary'] = secondarygroups

            # match up against ldap data
            try:
                result = ldap_conn.search_s('ou=People,dc=triumvirate,dc=rocks', ldap.SCOPE_SUBTREE, filterstr='(&(objectclass=pilot)(characterName={0}))'.format(charname), attrlist=['authGroup', 'accountstatus', 'uid'])
            except ldap.LDAPError as error:
                _logger.log('[' + __name__ + '] unable to fetch ldap user {0}: {1}'.format(charid,error),_logger.LogLevel.ERROR)

            if len(result) == 0:
                # you WILL be dealt with later!
#                print('orphan user:"{}"'.format(charname))
                orphan += 1
                users[charname]['charid'] = None
                users[charname]['authgroups'] = []
                users[charname]['accountstatus'] = None
            else:
                dn, result = result[0]
                users[charname]['dn'] = dn

                # character ID is primary to all ldap entries.
                charid = result['uid'][0].decode('utf-8')
                charid = int(charid)
                users[charname]['charid'] = charid

                # account status is the equivalent of forum primary group
                users[charname]['accountstatus'] = result['accountStatus'][0].decode('utf-8')

                # auth groups are functionally forum secondary groups

                authgroups = result['authGroup']
                authgroups = list(map(lambda x: x.decode('utf-8'), authgroups))
                users[charname]['authgroups'] = authgroups


        # last but not least
        page += 1

    # postprocessing

    # remove special users from consideration.
    # may be worth tagging directly in ldap some day?

    special = [ 'Admin', 'Sovereign' ]

    for user in special:
        users.pop(user, None)

    _logger.log('[' + __name__ + '] orphan forum users: {0}'.format(orphan),_logger.LogLevel.INFO)

    # map each user to a charID given that the username is exactly
    # a character name

    really_orphan = 0

    for charname in users:
        user = users[charname]
        primary = user['primary']

        if user['charid'] == None:
            # need to map the forum username to a character id
            query = { 'categories': 'character', 'datasource': 'tranquility', 'language': 'en-us', 'search': charname, 'strict': 'true' }
            query = urllib.parse.urlencode(query)
            esi_url = base_url + 'search/?' + query
            code, result = common.request_esi.esi(__name__, esi_url, 'get')
            _logger.log('[' + __name__ + '] /search output: {}'.format(result), _logger.LogLevel.DEBUG)

            if not code == 200:
                print(result)
            if len(result) == 0:
                really_orphan += 1
                users[charname]['doomheim'] = True
            if len(result) == 1:
                users[charname]['charid'] = result['character'][0]
            if len(result) >= 2:
                print('multiple character return from /search')
                print(esi_url)
                print(charname)

    _logger.log('[' + __name__ + '] doomheim forum users: {0}'.format(really_orphan),_logger.LogLevel.INFO)

    # at this point every forum user has been mapped to their character id either via ldap or esi /search

    # work through each user and determine if they are correctly setup on the forums

    non_tri = 0
    for charname in users:

        charid = users[charname]['charid']

        if users[charname]['doomheim'] == True:
            forumpurge(charname)
            continue

        # get forum groups

        cursor = sql_conn.cursor()
        query = 'SELECT member_group_id, mgroup_others, ip_address FROM core_members WHERE name=%s'
        try:
            rowcount = cursor.execute(query, (charname,))
            row = cursor.fetchone()
        except Exception as err:
            _logger.log('[' + __name__ + '] mysql error: ' + str(err), _logger.LogLevel.ERROR)
            return

        if rowcount == 0:
            # this SHOULDN'T happen
            _logger.log('[' + __name__ + '] unable to find forum user: {0}'.format(user), _logger.LogLevel.WARN)

        primary_group = row[0]
        secondary_groups = row[1].split(',')
        forum_lastip = row[2]

        # get character affiliations
        request_url = base_url + 'characters/affiliation/?datasource=tranquility'
        data = '[{}]'.format(charid)
        code, result = common.request_esi.esi(__name__, request_url, method='post', data=data)

        if not code == 200:
            # something broke severely
            _logger.log('[' + __name__ + '] affiliations API error {0}: {1}'.format(code, result['error']),
                        _logger.LogLevel.ERROR)
            error = result['error']
            result = {'code': code, 'error': error}
            print('oops looking at {0}: {1} {2}'.format(charid, code, result))

        corpid = result[0]['corporation_id']
        try:
            allianceid = result[0]['alliance_id']
        except KeyError:
            allianceid = 0

        ## start doing checks

        # only people in tri get anything other than public access on the tri forums
        # forum public/unprivileged groupid: 2

        vanguard = forum_mappings.keys()

        if allianceid not in vanguard and primary_group != 2:

            # this char is not in a vanguard alliance but has non-public forum access

            forumpurge(charname)

            # log

            _logger.securitylog(__name__, 'forum demotion', charid=charid, charname=charname, ipaddress=forum_lastip)
            msg = 'non-vanguard character with privileged access demoted. charname: {0} ({1}), alliance: {2}, primary group: {3}, secondary group(s): {4}, last ip: {5}'.format(
                charname, charid, allianceid, primary_group, secondary_groups, forum_lastip
            )
            _logger.log('[' + __name__ + '] {}'.format(msg),_logger.LogLevel.WARNING)
            non_tri += 1

    _logger.log('[' + __name__ + '] non-vanguard forum users removed: {0}'.format(non_tri),_logger.LogLevel.INFO)

def forumpurge (charname):
    # remove their access
    
    import common.logger as _logger
    import common.credentials.forums as _forumcreds
    import MySQLdb as mysql
    
    try:
        sql_conn = mysql.connect(
            database=_forumcreds.mysql_db,
            user=_forumcreds.mysql_user,
            password=_forumcreds.mysql_pass,
            host=_forumcreds.mysql_host)
    except mysql.Error as err:
        _logger.log('[' + __name__ + '] mysql error: ' + str(err), _logger.LogLevel.ERROR)
        return False

    cursor = sql_conn.cursor()

    # remove secondary groups

    query = 'UPDATE core_members SET mgroup_others = "" WHERE name = %s'
    try:
        cursor.execute(query, (charname,))
    except Exception as err:
        _logger.log('[' + __name__ + '] mysql error: ' + str(err), _logger.LogLevel.ERROR)
        return False

    # set them to the public group
    query = 'UPDATE core_members SET member_group_id = "2" WHERE name = %s'
    try:
        cursor.execute(query, (charname,))
    except Exception as err:
        _logger.log('[' + __name__ + '] mysql error: ' + str(err), _logger.LogLevel.ERROR)
        return False

    sql_conn.commit()
    cursor.close()
    return True
