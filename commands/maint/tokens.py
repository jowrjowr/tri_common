import common.logger as _logger
import common.maint.eve.refresh as _everefresh
import common.ldaphelpers as _ldaphelpers
import common.request_esi
import time
import ldap

from tri_core.common.storetokens import storetokens
from concurrent.futures import ThreadPoolExecutor, as_completed

def maint_tokens():


    ldap_conn = _ldaphelpers.ldap_binding(__name__)

    if ldap_conn == None:
        _logger.log('[' + __name__ + '] LDAP connection error: {}'.format(error),_logger.LogLevel.ERROR)
        return

    # grab each token from ldap

    dn = 'ou=People,dc=triumvirate,dc=rocks'
    filterstr = '(&(objectclass=pilot)(uid=*)(esiRefreshToken=*))'
    attrlist = ['esiRefreshToken', 'esiScope', 'uid', 'corporationRole']

    code, result = _ldaphelpers.ldap_search(__name__, dn, filterstr, attrlist)

    if code == False:
        return

    _logger.log('[' + __name__ + '] ldap users with defined refresh tokens: {0}'.format(len(result)),_logger.LogLevel.INFO)

    evetokens = dict()

    for dn, info in result.items():

        rtoken = info.get('esiRefreshToken')

        if rtoken == None:
            # can't refresh something that isn't there
            continue

        evetokens[dn] = dict()
        evetokens[dn]['dn'] = dn
        evetokens[dn]['rtoken'] = rtoken
        evetokens[dn]['uid'] = int( info.get('uid') )
        evetokens[dn]['scopes'] = info.get('esiScope')
        evetokens[dn]['roles'] = info.get('corporationRole')

    ldap_conn.unbind()

    # dump the tokens into a pool to bulk manage

    with ThreadPoolExecutor(40) as executor:
        futures = { executor.submit(tokenthings, evetokens[dn]): dn for dn in evetokens.keys() }
        for future in as_completed(futures):
            data = future.result()



def tokenthings(userdata):

    # wrap around do_esi so we can do retries!

    retry_max = 5
    retry_count = 0
    sleep = 1
    function = __name__

    while (retry_count < retry_max):
        if retry_count > 0:
            _logger.log('[' + function + '] token update retry {0} of {1}'.format(retry_count, retry_max), _logger.LogLevel.WARNING)

        result = tokenthings_again(userdata)
        if result == False:
            retry_count += 1
            _logger.log('[' + function + '] token update failed. sleeping {0} seconds before retrying'.format(sleep), _logger.LogLevel.WARNING)
            time.sleep(sleep)
        else:
            return True
    _logger.log('[' + function + '] token update failed {0} times. giving up. '.format(retry_max), _logger.LogLevel.WARNING)
    return False


def tokenthings_again(tokendata):

    dn = tokendata['dn']
    charid = tokendata['uid']
    roles = tokendata['roles']
    ldap_scopes = tokendata['scopes']
    old_rtoken = tokendata['rtoken']
    function = __name__

    ldap_conn = _ldaphelpers.ldap_binding(__name__)

    if ldap_conn == None:
        _logger.log('[' + __name__ + '] LDAP connection error: {}'.format(error),_logger.LogLevel.ERROR)
        return

    if roles is None:
        roles = []
    if ldap_scopes is None:
        ldap_scopes = []

    _logger.log('[' + __name__ + '] updating token for charid {0}'.format(charid), _logger.LogLevel.DEBUG)

    result, code = _everefresh.refresh_token(old_rtoken)

    if code is not True:
        # broken token, or broken oauth?
        # the distinction matters.
        # see env/lib/python3.5/site-packages/oauthlib/oauth2/rfc6749/errors.py

        _logger.log('[' + __name__ + '] unable to refresh token for charid {0}: {1}'.format(charid, result), _logger.LogLevel.INFO)

        # only these exception types are valid reasons to purge a token
        purgetype = [ 'InvalidGrantError', 'UnauthorizedClientError', 'InvalidClientError' ]

        if result in purgetype:

            # purge the entry from the ldap user

            mod_attrs = []
            mod_attrs.append((ldap.MOD_REPLACE, 'esiRefreshToken', None ))
            mod_attrs.append((ldap.MOD_REPLACE, 'esiAccessToken', None ))
            mod_attrs.append((ldap.MOD_REPLACE, 'esiAccessTokenExpires', None ))
            try:
                ldap_conn.modify_s(dn, mod_attrs)
            except ldap.LDAPError as error:
                _logger.log('[' + __name__ + '] unable to purge rtoken entry for {0}: {1}'.format(dn, error),_logger.LogLevel.ERROR)
                ldap_conn.unbind()
                return False

            ldap_conn.unbind()
            return True
            _logger.log('[' + __name__ + '] invalid token entries purged for user {}'.format(dn), _logger.LogLevel.INFO)

        # either way, this has failed

        ldap_conn.unbind()
        return False

    atoken = result.get('access_token')
    rtoken = result.get('refresh_token')
    expires = result.get('expires_at')

    # store the updated token
    result, value = storetokens(charid, atoken, rtoken, expires)

    if result == False:
        _logger.log('[' + __name__ + '] unable to store tokens for user {}'.format(dn), _logger.LogLevel.ERROR)
        ldap_conn.unbind()
        return False

    # the updated token is now in LDAP

    mod_attrs = []

    # fetch all corporation roles for the updated token

    request_url = 'characters/{0}/roles/?datasource=tranquility'.format(charid)
    code, result = common.request_esi.esi(__name__, request_url, method='get', charid=charid, version='v1')

    if code == 403:
        error = 'no perms to read roles for {0}: ({1}) {2}'.format(charid, code, result['error'])
        _logger.log('[' + function + '] ' + error,_logger.LogLevel.DEBUG)
    elif not code == 200:
        error = 'unable to get character roles for {0}: ({1}) {2}'.format(charid, code, result['error'])
        _logger.log('[' + function + '] ' + error,_logger.LogLevel.ERROR)
    else:

        # figure out what needs to be added and removed from ldap

        missing_roles = set(result) - set(roles)
        extra_roles = set(roles) - set(result)

        for missing in list(missing_roles):
            missing = missing.encode('utf-8')
            mod_attrs.append((ldap.MOD_ADD, 'corporationRole', [ missing ] ))

        for extra in list(extra_roles):
            extra = extra.encode('utf-8')
            mod_attrs.append((ldap.MOD_DELETE, 'corporationRole', [ extra ] ))

    # determine the scopes the token has access to
    # the verify url is specifically not versioned
    # the token parameter is to bypass caching

    verify_url = 'verify/?datasource=tranquility&token={0}'.format(atoken)
    code, result = common.request_esi.esi(__name__, verify_url, method='get', base='esi_verify')
    if not code == 200:
        _logger.log('[' + __name__ + '] unable to get token information for {0}: {1}'.format(charid, result['error']),_logger.LogLevel.ERROR)
        ldap_conn.unbind()
        return

    # character scopes come out in a space delimited list
    token_scopes = result['Scopes']
    token_scopes = token_scopes.split()
    token_charid = int(result['CharacterID'])

    if not token_charid == charid:
        _logger.log('[' + __name__ + '] stored token for charid {0} belongs to charid {1}'.format(charid, token_charid),_logger.LogLevel.ERROR)
        ldap_conn.unbind()
        return
    # so given an array of scopes, let's check that what we want is in the list of scopes the character's token has

    missing_scopes = set(token_scopes) - set(ldap_scopes)
    extra_scopes = set(ldap_scopes) - set(token_scopes)

    for missing in list(missing_scopes):
        missing = missing.encode('utf-8')
        mod_attrs.append((ldap.MOD_ADD, 'esiScope', [ missing ]))

    for extra in list(extra_scopes):
        extra = extra.encode('utf-8')
        mod_attrs.append((ldap.MOD_DELETE, 'esiScope', [ extra ] ))

    if len(mod_attrs) > 0:
        try:
            ldap_conn.modify_s(dn, mod_attrs)
        except ldap.LDAPError as error:
            _logger.log('[' + __name__ + '] unable to update uid {0}: {1}'.format(charid, error),_logger.LogLevel.ERROR)
    ldap_conn.unbind()
