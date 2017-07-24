def storetokens(charid, atoken, rtoken, expires=None):
    # refresh a characters token store
    # this will also put in a really basic entry into ldap/mysql

    import common.logger as _logger
    import common.credentials.ldap as _ldap
    import ldap
    import time

    _logger.log('[' + __name__ + '] updating tokens for user {}'.format(charid),_logger.LogLevel.DEBUG)

    # the ldap way
    ldap_conn = ldap.initialize(_ldap.ldap_host, bytes_mode=False)
    try:
        ldap_conn.simple_bind_s(_ldap.admin_dn, _ldap.admin_dn_password)
    except ldap.LDAPError as error:
        _logger.log('[' + __name__ + '] LDAP connection error: {}'.format(error),_logger.LogLevel.ERROR)
        return(False, 'error')

    # verify existence. not sure what ldap does if you try to modify something that doesn't exist
    try:
        users = ldap_conn.search_s('ou=People,dc=triumvirate,dc=rocks', ldap.SCOPE_SUBTREE, filterstr='(&(objectclass=pilot)(uid={0}))'.format(charid), attrlist=['authGroup'])
        user_count = users.__len__()
    except ldap.LDAPError as error:
        _logger.log('[' + __name__ + '] unable to fetch ldap user {0}: {1}'.format(charid,error),_logger.LogLevel.ERROR)

    if user_count == 0:
        # why are we modifyin something that doesn't exist?
        return(False, 'error')

    dn = users[0][0]
    atoken = [ atoken.encode('utf-8') ]
    rtoken = [ rtoken.encode('utf-8') ]

    if expires == None:
        # set expiration to 'now'
        expires = time.time()

    expires = [ str(expires).encode('utf-8') ]
    mod_attrs = []
    mod_attrs.append((ldap.MOD_REPLACE, 'esiAccessToken', atoken ))
    mod_attrs.append((ldap.MOD_REPLACE, 'esiRefreshToken', rtoken ))
    mod_attrs.append((ldap.MOD_REPLACE, 'esiAccessTokenExpires', expires ))

    try:
        result = ldap_conn.modify_s(dn, mod_attrs)
    except ldap.LDAPError as error:
        _logger.log('[' + __name__ + '] unable to update tokens for {0}: {1}'.format(charid,error),_logger.LogLevel.ERROR)
        return(False, 'error')

    _logger.log('[' + __name__ + '] tokens for user {0} updated (ldap)'.format(charid),_logger.LogLevel.DEBUG)
    return(True, 'success')
