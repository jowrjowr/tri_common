def ldap_search(function, dn, filter, attributes):

    import ldap
    import ldap.modlist
    import common.logger as _logger
    import common.credentials.ldap as _ldap
    from flask import Response, request

    # initialize connections

    try:
        ldap_conn = ldap.initialize(_ldap.ldap_host, bytes_mode=False)
        ldap_conn.simple_bind_s(_ldap.admin_dn, _ldap.admin_dn_password)
    except ldap.LDAPError as error:
        msg = 'LDAP connection error: {}'.format(error)
        _logger.log('[' + function + '] {}'.format(msg),_logger.LogLevel.ERROR)
        return False, msg

    try:
        result = ldap_conn.search_s(
            dn,
            ldap.SCOPE_SUBTREE,
            filterstr=filter,
            attrlist=attributes,
        )
        result_count = result.__len__()
    except ldap.LDAPError as error:
        msg = 'unable to fetch ldap information: {}'.format(error)
        _logger.log('[' + function + '] {}'.format(msg),_logger.LogLevel.ERROR)
        return False, msg

    if result_count == 0:
        # treating only hard fails as failure
        return True, None

    # construct the response
    response = dict()
    for object in result:
        # split off the dn/info pair
        dn, info = object
        details = dict()

        for attribute in attributes:
            # we won't always get the desired attribute
            try:
                # only return an array for multiple items
                # or authGroup, a helpful typecast
                if len(info[attribute]) > 1 or attribute == 'authGroup':
                    details[attribute] = list( map(lambda x: x.decode('utf-8'), info[attribute]) )
                else:
                    details[attribute] = info[attribute][0].decode('utf-8')
            except Exception as error:
                _logger.log('[' + function + '] dn {0} missing attribute {1}'.format(dn, attribute),_logger.LogLevel.DEBUG)
                details[attribute] = None

        response[dn] = details

    return True, response

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

