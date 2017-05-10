def audit_supers():
    import ldap
    import ldap.modlist
    import common.logger as _logger
    import common.credentials.ldap as _ldap

    _logger.log('[' + __name__ + '] auditing supers', _logger.LogLevel.INFO)

    ldap_conn = ldap.initialize(_ldap.ldap_host, bytes_mode=False)

    try:
        ldap_conn.simple_bind_s(_ldap.admin_dn, _ldap.admin_dn_password)
    except ldap.LDAPError as error:
        _logger.log('[' + __name__ + '] LDAP connection error: {}'.format(error), _logger.LogLevel.ERROR)

    # fetch all the users

    try:
        users = ldap_conn.search_s('ou=People,dc=triumvirate,dc=rocks', ldap.SCOPE_SUBTREE,
                                   filterstr='(&(objectclass=pilot)(authGroup=trisupers))',
                                   attrlist=['characterName', 'alliance, corporation, esiAccessToken'])
        user_count = users.__len__()
        _logger.log('[' + __name__ + '] total ldap super users: {}'.format(user_count), _logger.LogLevel.DEBUG)
    except ldap.LDAPError as error:
        _logger.log('[' + __name__ + '] unable to fetch ldap users: {}'.format(error), _logger.LogLevel.ERROR)
        return

    for user in users:
        print(user)