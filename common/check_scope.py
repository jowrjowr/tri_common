import common.logger as _logger
import common.ldaphelpers as _ldaphelpers

def check_scope(function, charid, scopes):

    # we want to check an array of scopes and make sure that the token has access to them

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

    result = info.get('esiScope')

    char_scopes = set(result)
    intersection = char_scopes.intersection(scopes)

    if len(intersection) > 0:
        return True, ''
    else:
        return False, ''
