
def check_scope(function, charid, scopes, atoken=None):

    import common.logger as _logger
    import common.ldaphelpers as _ldaphelpers
    import common.request_esi

    # we want to check an array of scopes and make sure that the token has access to them

    if atoken is not None:
        # grap token scopes direct from token

        verify_url = 'verify/?token={0}'.format(atoken)
        code, result = common.request_esi.esi(__name__, verify_url, method='get', base='esi_verify')
        if not code == 200:
            _logger.log('[' + __name__ + '] unable to get token information for {0}: {1}'.format(charid, result),_logger.LogLevel.ERROR)
            return 'error', 'broken verify request'
        token_scopes = result['Scopes']
        token_scopes = token_scopes.split()
    else:

        # grab token scopes from ldap
        dn = 'ou=People,dc=triumvirate,dc=rocks'
        filterstr = 'uid={}'.format(charid)
        attrlist = ['esiScope']

        code, result = _ldaphelpers.ldap_search(__name__, dn, filterstr, attrlist)

        if code == False:
            _logger.log('[' + __name__ + '] LDAP connection error: {}'.format(error),_logger.LogLevel.ERROR)
            return

        if result == None:
            return

        (dn, info), = result.items()

        token_scopes = info.get('esiScope')

    if token_scopes == None:
        return False, ''

    token_scopes = set(token_scopes)
    intersection = token_scopes.intersection(scopes)

    if len(intersection) > 0:
        return True, ''
    else:
        return False, ''
