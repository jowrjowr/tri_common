def audit_forums():

    import common.request_forums as _forums
    import common.logger as _logger
    import common.credentials.ldap as _ldap
    import common.request_esi
    from common.api import base_url
    from common.graphite import sendmetric
    from collections import defaultdict
    import ldap
    import json
    import urllib
    import html

    _logger.log('[' + __name__ + '] auditing forums',_logger.LogLevel.INFO)

    # setup ldap
    ldap_conn = ldap.initialize(_ldap.ldap_host, bytes_mode=False)
    try:
        ldap_conn.simple_bind_s(_ldap.admin_dn, _ldap.admin_dn_password)
    except ldap.LDAPError as error:
        _logger.log('[' + __name__ + '] LDAP connection error: {}'.format(error),_logger.LogLevel.ERROR)
        return False

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
#        print(response)
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

    
# infidel?
