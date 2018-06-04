import common.logger as _logger
import common.ldaphelpers as _ldaphelpers

def check_role(charid, roles):

    # check to make sure that the user has the expected corp roles

    # grab roles from ldap
    dn = 'ou=People,dc=triumvirate,dc=rocks'
    filterstr = 'uid={}'.format(charid)
    attrlist = [ 'corporationRole', 'corporationName' ]

    code, result = _ldaphelpers.ldap_search(__name__, dn, filterstr, attrlist)

    if code == False:
        _logger.log('[' + __name__ + '] LDAP connection error: {}'.format(error),_logger.LogLevel.ERROR)
        return False

    (dn, info), = result.items()

    if result == None:
        return False

    result = info.get('corporationRole')

    if result == None:
        return False

    char_roles = set(result)
    intersection = char_roles.intersection(roles)

    if len(intersection) > 0:
        return True
    else:
        return False
