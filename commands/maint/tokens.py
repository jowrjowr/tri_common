def maint_tokens():

    from tri_core.common.storetokens import storetokens
    import common.logger as _logger
    import common.maint.discord.refresh as _discordrefresh
    import common.maint.eve.refresh as _everefresh
    import common.credentials.ldap as _ldap
    import ldap
    import json
    import time
    import datetime

    # bindings

    ldap_conn = ldap.initialize(_ldap.ldap_host, bytes_mode=False)
    try:
        ldap_conn.simple_bind_s(_ldap.admin_dn, _ldap.admin_dn_password)
    except ldap.LDAPError as error:
        _logger.log('[' + __name__ + '] LDAP connection error: {}'.format(error),_logger.LogLevel.ERROR)
        return

    # grab each token from ldap

    try:
        # search specifically for users with a defined uid (everyone, tbh) and a defined refresh token (not everyone)
        result = ldap_conn.search_s(
            'ou=People,dc=triumvirate,dc=rocks',
            ldap.SCOPE_SUBTREE,
            filterstr='(&(objectclass=pilot)(uid=*)(esiRefreshToken=*))',
            attrlist=['esiRefreshToken', 'uid']
        )
        token_count = result.__len__()
    except ldap.LDAPError as error:
        _logger.log('[' + __name__ + '] unable to fetch ldap information: {}'.format(error),_logger.LogLevel.ERROR)
        return

    _logger.log('[' + __name__ + '] ldap users with defined refresh tokens: {0}'.format(token_count),_logger.LogLevel.INFO)

    evetokens = dict()

    for object in result:
        dn, info = object
        rtoken = info['esiRefreshToken'][0].decode('utf-8')
        uid = info['uid'][0].decode('utf-8')
        evetokens[dn] = dict()
        evetokens[dn]['rtoken'] = rtoken
        evetokens[dn]['uid'] = uid

    # work with each individual token

    eve_broketokens = 0
    discord_broketokens = 0

    for user in evetokens:
        dn = user
        charid = evetokens[user]['uid']
        old_rtoken = evetokens[user]['rtoken']
        purge = False

        result, code = _everefresh.refresh_token(old_rtoken)

        if code == True:
            atoken = result['access_token']
            rtoken = result['refresh_token']
            expires = result['expires_at']

            # store the updated token
            result, value = storetokens(charid, atoken, rtoken)

            if result == True:
                _logger.log('[' + __name__ + '] token entries updated for user {}'.format(dn), _logger.LogLevel.DEBUG)
            else:
                _logger.log('[' + __name__ + '] unable to store tokens for user {}'.format(dn), _logger.LogLevel.ERROR)
        else:
            # broken token, or broken oauth.
            # the distinction matters.
            # see env/lib/python3.5/site-packages/oauthlib/oauth2/rfc6749/errors.py

            _logger.log('[' + __name__ + '] unable to refresh token for charid {0}: {1}'.format(charid, result), _logger.LogLevel.INFO)

            # only these exception types are valid reasons to purge a token
            purgetype = [ 'InvalidGrantError', 'UnauthorizedClientError', 'InvalidClientError' ]

            if result in purgetype:

                eve_broketokens = eve_broketokens + 1

                # purge the entry from the ldap user
                mod_attrs = []
                mod_attrs.append((ldap.MOD_DELETE, 'esiAccessToken', None ))

                # for some reason sometimes there is only one of the access/refresh tokens even though they should come in pairs
                try:
                    result = ldap_conn.modify_s(dn, mod_attrs)
                except ldap.LDAPError as error:
                    _logger.log('[' + __name__ + '] unable to purge atoken entry for {0}: {1}'.format(dn, error),_logger.LogLevel.ERROR)

                mod_attrs = []
                mod_attrs.append((ldap.MOD_DELETE, 'esiRefreshToken', None ))
                try:
                    result = ldap_conn.modify_s(dn, mod_attrs)
                except ldap.LDAPError as error:
                    _logger.log('[' + __name__ + '] unable to purge rtoken entry for {0}: {1}'.format(dn, error),_logger.LogLevel.ERROR)

                _logger.log('[' + __name__ + '] invalid token entries purged for user {}'.format(dn), _logger.LogLevel.INFO)

    _logger.log('[' + __name__ + '] invalid tokens purged: {}'.format(eve_broketokens), _logger.LogLevel.INFO)

