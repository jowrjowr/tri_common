def purge_authgroups(dn, groups):
    import common.logger as _logger
    import common.credentials.ldap as _ldap
    import json
    import ldap
    import ldap.modlist

    # remove the authGroups from a user

    ldap_conn = ldap.initialize(_ldap.ldap_host, bytes_mode=False)
    try:
        ldap_conn.simple_bind_s(_ldap.admin_dn, _ldap.admin_dn_password)
    except ldap.LDAPError as error:
        _logger.log('[' + __name__ + '] LDAP connection error: {}'.format(error),_logger.LogLevel.ERROR)

    mod_attrs = []

    for group in groups:
        mod_attrs.append((ldap.MOD_DELETE, 'authGroup', group.encode('utf-8')))

    try:
        result = ldap_conn.modify_s(dn, mod_attrs)
        _logger.log('[' + __name__ + '] extra authgroups removed from dn {0}'.format(dn),_logger.LogLevel.INFO)
    except ldap.LDAPError as error:
        _logger.log('[' + __name__ + '] unable to update dn {0} accountStatus: {1}'.format(dn,error),_logger.LogLevel.ERROR)

def update_singlevalue(dn, attribute, value):
    import common.logger as _logger
    import common.credentials.ldap as _ldap
    import json
    import ldap
    import ldap.modlist

    # update the user's (single valued!) attribute to value
    # (it clobbers multivalued)

    ldap_conn = ldap.initialize(_ldap.ldap_host, bytes_mode=False)
    try:
        ldap_conn.simple_bind_s(_ldap.admin_dn, _ldap.admin_dn_password)
    except ldap.LDAPError as error:
        _logger.log('[' + __name__ + '] LDAP connection error: {}'.format(error),_logger.LogLevel.ERROR)

    mod_attrs = [ (ldap.MOD_REPLACE, attribute, value.encode('utf-8') ) ]

    try:
        result = ldap_conn.modify_s(dn, mod_attrs)
        _logger.log('[' + __name__ + '] dn {0} attribute {1} set to {2}'.format(dn, attribute, value),_logger.LogLevel.INFO)
    except ldap.LDAPError as error:
        _logger.log('[' + __name__ + '] unable to update dn {0} attribute {1}: {2}'.format(dn, attribute, error),_logger.LogLevel.ERROR)


def add_value(dn, attribute, value):
    import common.logger as _logger
    import common.credentials.ldap as _ldap
    import json
    import ldap
    import ldap.modlist

    # add an attribute to an empty/multivalued attribute

    ldap_conn = ldap.initialize(_ldap.ldap_host, bytes_mode=False)
    try:
        ldap_conn.simple_bind_s(_ldap.admin_dn, _ldap.admin_dn_password)
    except ldap.LDAPError as error:
        _logger.log('[' + __name__ + '] LDAP connection error: {}'.format(error),_logger.LogLevel.ERROR)

    mod_attrs = [ (ldap.MOD_ADD, attribute, value.encode('utf-8') ) ]

    try:
        result = ldap_conn.modify_s(dn, mod_attrs)
        _logger.log('[' + __name__ + '] dn {0} attribute {1} set to {2}'.format(dn, attribute, value),_logger.LogLevel.INFO)
    except ldap.LDAPError as error:
        _logger.log('[' + __name__ + '] unable to update dn {0} attribute {1}: {2}'.format(dn, attribute, error),_logger.LogLevel.ERROR)

