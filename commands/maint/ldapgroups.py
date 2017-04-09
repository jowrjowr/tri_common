def maint_ldapgroups():

    import ldap
    import ldap.modlist
    import common.logger as _logger
    import common.credentials.ldap as _ldap
    from collections import defaultdict
    _logger.log('[' + __name__ + '] refreshing ldap groups',_logger.LogLevel.INFO)

    # sadly ldap group memberships work this way :/

    ldap_conn = ldap.initialize(_ldap.ldap_host, bytes_mode=False)
    try:
        ldap_conn.simple_bind_s(_ldap.admin_dn, _ldap.admin_dn_password)
    except ldap.LDAPError as error:
        _logger.log('[' + __name__ + '] LDAP connection error: {}'.format(error),_logger.LogLevel.ERROR)

    # fetch all the users

    try:
        users = ldap_conn.search_s('ou=People,dc=triumvirate,dc=rocks', ldap.SCOPE_SUBTREE, filterstr='(objectclass=pilot)', attrlist=['authGroup'])
        user_count = users.__len__()
    except ldap.LDAPError as error:
        _logger.log('[' + __name__ + '] unable to fetch ldap users: {}'.format(error),_logger.LogLevel.ERROR)

    _logger.log('[' + __name__ + '] total ldap users: {}'.format(user_count),_logger.LogLevel.DEBUG)


    # form an dict of groups with each entry being
    # an array of user DNs that will populate the ldap group

    newgroupmembers = defaultdict(list)

    for user in users:
        dn, groups = user
        groups = groups['authGroup']
        groups = list(map(lambda x: x.decode('utf-8'), groups))
        for group in groups:
            newgroupmembers[group].append(dn)

    # now iterate through each group, and ldapmodify

    for group in newgroupmembers:
        _logger.log('[' + __name__ + '] updating group {0}'.format(group),_logger.LogLevel.DEBUG)
        dn = 'cn={},ou=Groups,dc=triumvirate,dc=rocks'.format(group)
        members = list(map(lambda x: x.encode('utf-8'), newgroupmembers[group]))
        # https://www.packtpub.com/books/content/python-ldap-applications-extra-ldap-operations-and-ldap-url-library
        mod_attrs = [ (ldap.MOD_REPLACE, 'member', members ) ]
        try:
            result = ldap_conn.modify_s(dn, mod_attrs)
        except ldap.LDAPError as error:
            _logger.log('[' + __name__ + '] unable to update group {0} memberlist: {1}'.format(group,error),_logger.LogLevel.ERROR)
        _logger.log('[' + __name__ + '] group {0} updated'.format(group),_logger.LogLevel.DEBUG)

    _logger.log('[' + __name__ + '] all ldap groups synchronized',_logger.LogLevel.DEBUG)
