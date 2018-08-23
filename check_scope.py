import logging
from common.verify import verify

def check_scope(charid, scopes, atoken=None):

    # import recursion protection since check_scope is used there

    import common.ldaphelpers as _ldaphelpers

    # we want to check an array of scopes and make sure that the token has access to them

    if not atoken:
        # grab token scopes from ldap
        dn = 'ou=People,dc=triumvirate,dc=rocks'
        filterstr = 'uid={}'.format(charid)
        attrlist = ['esiAccessToken']

        code, result = _ldaphelpers.ldap_search(__name__, dn, filterstr, attrlist)

        if code == False:
            msg = "LDAP connection error: {}".format(error)
            logging.error(msg)
            return None

        if result == None:
            return False

        (dn, info), = result.items()

        atoken = info.get('esiAccessToken')

    # grap token scopes direct from token
    try:
        _, charname, token_scopes = verify(atoken)
    except Exception as e:
        msg = "unable to unpack token: {}".format(e)
        return None

    token_scopes = set(token_scopes)
    intersection = token_scopes.intersection(scopes)

    if len(intersection) > 0:
        return True

    return False
