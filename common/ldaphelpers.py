import common.logger as _logger
import common.credentials.ldap as _ldap
import common.esihelpers as _esihelpers
import common.request_esi
import ldap
import hashlib
import uuid

from passlib.hash import ldap_salted_sha1

def ldap_create_stub(function, charname):

    # make a very basic ldap entry for charname


    # find the user's uid before proceeding further

    result = _esihelpers.user_search(charname)
    user = dict()

    if result == False:
        # damage
        msg = 'ESI search error'
        return False, msg
    elif len(result) is 0:
        # nothing found.
        msg = 'no such character'
        return False, msg
    elif len(result) > 1:
        # too much found
        msg = 'too many results'
        return False, msg

    # okay hopefuly nothing else fucked up by now

    charid = result['character'][0]

    user['uid'] = charid

    # get affiliations and shit

    try:
        request_url = 'characters/{0}/?datasource=tranquility'.format(charid)
        code, result = common.request_esi.esi(__name__, request_url, method='get', version='v4')
    except Exception as error:
        _logger.log('[' + __name__ + '] /characters API error {0}: {1}'.format(code, result['error']), _logger.LogLevel.ERROR)
        return False

    charname = result['name']
    user['characterName'] = charname

    cn = charname.replace(" ", '')
    cn = cn.replace("'", '')
    cn = cn.lower()
    dn = "cn={},ou=People,dc=triumvirate,dc=rocks".format(cn)

    user['cn'] = cn
    user['sn'] = cn
    user['accountStatus'] = 'public'
    user['authGroup'] = 'public'

    # build the stub

    attrs = []

    # generate a bullshit password

    password = uuid.uuid4().hex
    password_hash = ldap_salted_sha1.hash(password)

    user['userPassword'] = password_hash

    # handle rest of crap

    for item in user.keys():
        user[item] = [ str(user[item]).encode('utf-8') ]
        attrs.append((item, user[item]))

    attrs.append(('objectClass', ['top'.encode('utf-8'), 'pilot'.encode('utf-8'), 'simpleSecurityObject'.encode('utf-8'), 'organizationalPerson'.encode('utf-8')]))

    # ldap binding
    ldap_conn = ldap.initialize(_ldap.ldap_host, bytes_mode=False)
    try:
        ldap_conn.simple_bind_s(_ldap.admin_dn, _ldap.admin_dn_password)
    except ldap.LDAPError as error:
        _logger.log('[' + __name__ + '] LDAP connection error: {}'.format(error),_logger.LogLevel.ERROR)
        return False, error

    # add the stub to ldap

    try:
        ldap_conn.add_s(dn, attrs)
    except Exception as error:
        return False, error
    finally:
        ldap_conn.unbind()

    # no error. done!

    return True, None

def ldap_binding(function):

    # make an ldap connection

    ldap_conn = ldap.initialize(_ldap.ldap_host, bytes_mode=False)
    try:
        ldap_conn.simple_bind_s(_ldap.admin_dn, _ldap.admin_dn_password)
    except ldap.LDAPError as error:
        _logger.log('[' + __name__ + '] LDAP connection error: {}'.format(error),_logger.LogLevel.ERROR)
        return None

    return ldap_conn

def ldap_uid2name(function, uid):

    dn = 'ou=People,dc=triumvirate,dc=rocks'
    filterstr='(uid={})'.format(uid)
    attrlist=['uid', 'characterName']
    code, result = ldap_search(function, dn, filterstr, attrlist)

    if code == False:
        msg = 'unable to fetch ldap information: {}'.format(error)
        _logger.log('[' + function + '] {}'.format(msg),_logger.LogLevel.ERROR)
        return None

    if result == None:
        msg = 'uid {0} not in ldap'.format(uid)
        _logger.log('[' + function + '] {}'.format(msg),_logger.LogLevel.DEBUG)
        return None
    (dn, info), = result.items()

    return info

def ldap_cn2id(function, cn):
    import common.logger as _logger

    dn = 'ou=People,dc=triumvirate,dc=rocks'
    filterstr='(cn={})'.format(cn)
    attrlist=['uid']
    code, result = ldap_search(function, dn, filterstr, attrlist)

    if code == False:
        msg = 'unable to fetch ldap information: {}'.format(error)
        _logger.log('[' + function + '] {}'.format(msg),_logger.LogLevel.ERROR)
        return None

    if result == None:
        msg = 'cn {0} not in ldap'.format(cn)
        _logger.log('[' + function + '] {}'.format(msg),_logger.LogLevel.DEBUG)
        return None
    (dn, info), = result.items()

    return info


def ldap_name2id(function, charname):
    import common.logger as _logger

    dn = 'ou=People,dc=triumvirate,dc=rocks'
    filterstr='(characterName:caseIgnoreMatch:={})'.format(charname)
    attrlist=['uid']
    code, result = ldap_search(function, dn, filterstr, attrlist)

    if code == False:
        msg = 'unable to fetch ldap information: {}'.format(error)
        _logger.log('[' + function + '] {}'.format(msg),_logger.LogLevel.ERROR)
        return None

    if result == None:
        msg = 'charname {0} not in ldap'.format(charid)
        _logger.log('[' + function + '] {}'.format(msg),_logger.LogLevel.DEBUG)
        return None
    (dn, info), = result.items()

    return info

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

    ldap_conn.unbind()
    return True, response

def purge_authgroups(dn, groups):
    import common.logger as _logger
    import common.credentials.ldap as _ldap
    import json
    import ldap
    import ldap.modlist

    if groups == []:
        return

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
        _logger.log('[' + __name__ + '] extra authgroups removed from dn {0}: {1}'.format(dn, groups),_logger.LogLevel.INFO)
    except ldap.LDAPError as error:
        _logger.log('[' + __name__ + '] unable to update dn {0} accountStatus: {1}'.format(dn,error),_logger.LogLevel.ERROR)

    ldap_conn.unbind()

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

    if value is None:
        mod_attrs = [ (ldap.MOD_DELETE, attribute, None) ]
    else:
        mod_attrs = [ (ldap.MOD_REPLACE, attribute, value.encode('utf-8') ) ]

    try:
        result = ldap_conn.modify_s(dn, mod_attrs)
        _logger.log('[' + __name__ + '] dn {0} attribute {1} set to {2}'.format(dn, attribute, value),_logger.LogLevel.INFO)
    except ldap.LDAPError as error:
        _logger.log('[' + __name__ + '] unable to update dn {0} attribute {1}: {2}'.format(dn, attribute, error),_logger.LogLevel.ERROR)
    ldap_conn.unbind()

def ldap_adduser(dn, attributes):

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
        return False
    # https://access.redhat.com/documentation/en-US/Red_Hat_Directory_Server/8.0/html/Configuration_and_Command_Reference/Configuration_Command_File_Reference-Access_Log_and_Connection_Code_Reference.html
    try:
        ldap_conn.add_s(dn, attributes)
        _logger.log('[' + __name__ + '] created ldap dn {0}'.format(dn),_logger.LogLevel.INFO)
        return True
    except ldap.LDAPError as error:
        _logger.log('[' + __name__ + '] unable to create ldap dn {0}: {1}'.format(dn,error),_logger.LogLevel.ERROR)
        return False
    ldap_conn.unbind()

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
    ldap_conn.unbind()

def ldap_altupdate(function, main_charid, alt_charid):
    import ldap
    import common.credentials.ldap as _ldap
    import common.logger as _logger

    # verify that the alt exists

    dn = 'ou=People,dc=triumvirate,dc=rocks'
    filterstr = 'uid={0}'.format(alt_charid)
    attributes = [ 'uid', 'altOf' ]
    code, result = ldap_search(function, dn, filterstr, attributes)

    if code == False:
        msg = 'unable to connect to ldap: {}'.format(result)
        _logger.log('[' + function + '] {}'.format(msg),_logger.LogLevel.ERROR)
        return False, msg

    if result == None:
        msg = 'alt {0} does not exist'.format(alt_charid)
        _logger.log('[' + function + '] {}'.format(msg),_logger.LogLevel.WARNING)
        return False, msg

    # just need the dn
    (dn, info), = result.items()

    old_main = info['altOf']

    if main_charid == old_main:
        # no change
        return None, None

    msg = 'updating {0} from altOf={1} to altOf={2}'.format(alt_charid, old_main, main_charid)
    _logger.log('[' + function + '] {}'.format(msg),_logger.LogLevel.INFO)

    # setup the ldap connection

    ldap_conn = ldap.initialize(_ldap.ldap_host, bytes_mode=False)
    try:
        ldap_conn.simple_bind_s(_ldap.admin_dn, _ldap.admin_dn_password)
    except ldap.LDAPError as error:
        msg = 'unable to connect to ldap: {}'.format(error)
        _logger.log('[' + function + '] {}'.format(msg),_logger.LogLevel.ERROR)
        return False, msg

    # adjust altOf

    if main_charid == None:
        mod_attrs = [ (ldap.MOD_DELETE, 'altOf', None ) ]
    else:
        change = str(main_charid).encode('utf-8')
        mod_attrs = [ (ldap.MOD_REPLACE, 'altOf', [ change ] ) ]

    # commit

    try:
        result = ldap_conn.modify_s(dn, mod_attrs)
    except Exception as e:
        msg = 'unable to update existing user {0} in ldap: {1}'.format(alt_id, e)
        _logger.log('[' + function + '] {}'.format(msg),_logger.LogLevel.ERROR)
        return False, msg
    finally:
        ldap_conn.unbind()

    return True, None
