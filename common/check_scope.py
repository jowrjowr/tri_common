def check_scope(function, charid, scopes, atoken=None):

    import common.request_esi
    import common.logger as _logger
    import common.credentials.ldap as _ldap
    import ldap

    # we want to check an array of scopes and make sure that the token has access to them

    if atoken == None:
        # in case we want to try a token directly rather than fetch from ldap

        ldap_conn = ldap.initialize(_ldap.ldap_host, bytes_mode=False)
        try:
            ldap_conn.simple_bind_s(_ldap.admin_dn, _ldap.admin_dn_password)
        except ldap.LDAPError as error:
            _logger.log('[' + function + '] LDAP connection error: {}'.format(error),_logger.LogLevel.ERROR)
        # snag the token
        try:
            result = ldap_conn.search_s(
                'ou=People,dc=triumvirate,dc=rocks',
                ldap.SCOPE_SUBTREE,
                filterstr='(&(objectclass=pilot)(uid={0})(esiAccessToken=*))'.format(charid),
                attrlist=['esiAccessToken']
                )
            user_count = result.__len__()
        except ldap.LDAPError as error:
            _logger.log('[' + function + '] unable to fetch ldap information: {}'.format(error),_logger.LogLevel.ERROR)
            return 'error', 'broken ldap'
            # this shouldn't happen often tbh
        if user_count == 0:
            return 'error', 'no token in ldap'
        dn, atoken = result[0]
        atoken = atoken['esiAccessToken'][0].decode('utf-8')

    # determine the scopes the token has access to

    verify_url = 'verify'
    extraheaders = {'Authorization': 'Bearer ' + atoken }
    code, result = common.request_esi.esi(__name__, verify_url, method='get', base='oauth', extraheaders=extraheaders)
    if not code == 200:
        _logger.log('[' + __name__ + '] unable to get token information for {0}: {1}'.format(charid, result['error']),_logger.LogLevel.ERROR)
        return 'error', 'broken verify request'
    charscopes = result['Scopes']

    # so given an array of scopes, let's check that what we want is in the list of scopes the character's token has

    # character scopes come out in a space delimited list
    charscopes = charscopes.split()

    # i want the set difference to be what is in the requested scope list, but NOT in the available scope list.
    difference = set(scopes) - set(charscopes)

    if difference == set([]):
        # the scopes requested matches what's available
        return True, []
    else:
        return False, difference
