def maint_tokens():

    import common.logger as _logger
    import common.credentials.ldap as _ldap
    import ldap
    from concurrent.futures import ThreadPoolExecutor

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

    # dump the tokens into a pool to bulk manage

    with ThreadPoolExecutor(25) as executor:
        for user in evetokens:
            dn = user
            charid = evetokens[user]['uid']
            old_rtoken = evetokens[user]['rtoken']
            executor.submit(tokenthings, dn, charid, old_rtoken)

def tokenthings(dn, charid, old_rtoken):

    import common.logger as _logger
    import time

    # wrap around do_esi so we can do retries!

    retry_max = 5
    retry_count = 0
    sleep = 1
    function = __name__

    while (retry_count < retry_max):
        if retry_count > 0:
            _logger.log('[' + function + '] token update retry {0} of {1}'.format(retry_count, retry_max), _logger.LogLevel.WARNING)

        result = tokenthings_again(dn, charid, old_rtoken)
        if result == False:
            retry_count += 1
            _logger.log('[' + function + '] token update failed. sleeping {0} seconds before retrying'.format(sleep), _logger.LogLevel.WARNING)
            time.sleep(sleep)
        else:
            return True
    _logger.log('[' + function + '] token update failed {0} times. giving up. '.format(retry_max), _logger.LogLevel.WARNING)
    return False


def tokenthings_again(dn, charid, old_rtoken):
    from tri_core.common.storetokens import storetokens
    import common.logger as _logger
    import common.maint.eve.refresh as _everefresh
    import common.credentials.ldap as _ldap
    import ldap

    _logger.log('[' + __name__ + '] updating token for charid {0}'.format(charid), _logger.LogLevel.DEBUG)

    ldap_conn = ldap.initialize(_ldap.ldap_host, bytes_mode=False)
    try:
        ldap_conn.simple_bind_s(_ldap.admin_dn, _ldap.admin_dn_password)
    except ldap.LDAPError as error:
        _logger.log('[' + __name__ + '] LDAP connection error: {}'.format(error),_logger.LogLevel.ERROR)
        return False

    result, code = _everefresh.refresh_token(old_rtoken)

    if code == True:
        atoken = result['access_token']
        rtoken = result['refresh_token']
        expires = result['expires_at']
        # store the updated token
        result, value = storetokens(charid, atoken, rtoken, expires)

        if result == True:
            _logger.log('[' + __name__ + '] token entries updated for user {}'.format(dn), _logger.LogLevel.DEBUG)
            return True
        else:
            _logger.log('[' + __name__ + '] unable to store tokens for user {}'.format(dn), _logger.LogLevel.ERROR)
            return False
    else:
        # broken token, or broken oauth?
        # the distinction matters.
        # see env/lib/python3.5/site-packages/oauthlib/oauth2/rfc6749/errors.py

        _logger.log('[' + __name__ + '] unable to refresh token for charid {0}: {1}'.format(charid, result), _logger.LogLevel.INFO)

        # only these exception types are valid reasons to purge a token
        purgetype = [ 'InvalidGrantError', 'UnauthorizedClientError', 'InvalidClientError' ]

        if result in purgetype:

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
        # failed
        return False

