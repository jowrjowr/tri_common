import common.logger as _logger
import ldap
import hashlib
import uuid
import numbers
import json

import common.request_esi
import common.logger as _logger
import common.credentials.ldap as _ldap
import common.esihelpers as _esihelpers

from flask import Response, request
from passlib.hash import ldap_salted_sha1


def ldap_normalize_charname(charname):
    # solve this shit once and for all

    cn = charname.replace(" ", '')
    cn = cn.replace("'", '_')
    cn = cn.lower()

    dn = "cn={},ou=People,dc=triumvirate,dc=rocks".format(cn)

    return cn, dn


def ldap_create_stub(
    charname=None, charid=None, isalt=False,
    altof=None, accountstatus='public', authgroups=['public'],
    atoken=None, rtoken=None
    ):


    # make a very basic ldap entry for charname

    function = __name__

    user = dict()

    if charname is not None and charid is None:
        # making a stub based on a charid
        result = _esihelpers.user_search(charname)

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

        charid = result['character']

    if charid is None:
        msg = 'no charname, no charid'
        return False, msg

    # get affiliations and shit

    affiliations = _esihelpers.esi_affiliations(charid)

    charname = affiliations.get('charname')
    corpid = affiliations.get('corpid')
    corpname = affiliations.get('corporation_name')
    allianceid = affiliations.get('allianceid')
    alliancename = affiliations.get('alliancename')

    cn, dn = ldap_normalize_charname(charname)

    user['uid'] = charid
    user['altof'] = altof
    user['characterName'] = charname
    user['corporation'] = corpid

    if allianceid:
        user['alliance'] = allianceid

    user['cn'] = cn
    user['sn'] = cn
    user['accountStatus'] = accountstatus
    user['authGroup'] = authgroups

    print(accountstatus)

    if rtoken:
        user['esiAccessToken'] = atoken
        user['esiRefreshToken'] = rtoken

    # build the stub

    attrs = []

    # generate a bullshit password

    password = uuid.uuid4().hex
    password_hash = ldap_salted_sha1.hash(password)

    user['userPassword'] = password_hash

    # handle rest of crap

    for item in user.keys():

        # authgroup is a repeated attribute so has to be handled carefully

        if item == 'authGroup':
            newgroups = []
            for group in authgroups:
                group = str(group).encode('utf-8')
                newgroups.append(group)
            user['authGroup'] = newgroups
        else:
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

    return True, dn


def ldap_binding(function):

    # make an ldap connection

    ldap_conn = ldap.initialize(_ldap.ldap_host, bytes_mode=False)
    try:
        ldap_conn.simple_bind_s(_ldap.admin_dn, _ldap.admin_dn_password)
    except ldap.LDAPError as error:
        _logger.log('[' + __name__ + '] LDAP connection error: {}'.format(error),_logger.LogLevel.ERROR)
        return None

    return ldap_conn

def ldap_userinfo(uid):
    dn = 'ou=People,dc=triumvirate,dc=rocks'
    filterstr='(uid={})'.format(uid)
    attrlist=['characterName', 'uid', 'altOf', 'authGroup', 'accountStatus' ]
    code, result = ldap_search(__name__, dn, filterstr, attrlist)
    function = __name__
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

def ldap_uid2name(uid):

    dn = 'ou=People,dc=triumvirate,dc=rocks'
    filterstr='(uid={})'.format(uid)
    attrlist=['uid', 'characterName']
    code, result = ldap_search(__name__, dn, filterstr, attrlist)

    function = __name__

    if code == False:
        msg = 'unable to fetch ldap information: {}'.format(error)
        _logger.log('[' + function + '] {}'.format(msg),_logger.LogLevel.ERROR)
        return None

    if result == None:
        msg = 'uid {0} not in ldap'.format(uid)
        _logger.log('[' + function + '] {}'.format(msg),_logger.LogLevel.DEBUG)
        return None
    (dn, info), = result.items()

    return info['characterName']

def ldap_cn2id(function, cn):

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

                # attributes that are ALWAYS RETURNED AS A LIST

                forced_list = [ 'esiScope', 'corporationRole', 'authGroup' ]

                if len(info[attribute]) > 1 or attribute in forced_list:
                    details[attribute] = list( map(lambda x: x.decode('utf-8'), info[attribute]) )
                else:
                    details[attribute] = info[attribute][0].decode('utf-8')
                # force cast them to an empty array

                if attribute in forced_list and len(info[attribute]) == 222222222222220:
                    print('reeeee')
                    print(info[attribute])
                    print(details[attribute])
                    #details[attribute] = []

            except Exception as error:
                _logger.log('[' + function + '] dn {0} missing attribute {1}'.format(dn, attribute),_logger.LogLevel.DEBUG)
                details[attribute] = None

            # typecasting if appropriate
            if type(details[attribute]) is str:

                # NoneType contamination fix

                if details[attribute] == 'None':
                    details[attribute] = None

                # booleans

                elif details[attribute] == 'True':
                    details[attribute] = True

                elif details[attribute] == 'False':
                    details[attribute] = False

                # integer casting

                elif details[attribute].isdigit():
                    details[attribute] = int(details[attribute])

                # float casting
                else:
                    try:
                        details[attribute] = float(details[attribute])
                    except Exception as e:
                        pass

        response[dn] = details

    ldap_conn.unbind()
    return True, response

def purge_dn(dn):

    # remove the authGroups from a user

    ldap_conn = ldap.initialize(_ldap.ldap_host, bytes_mode=False)
    try:
        ldap_conn.simple_bind_s(_ldap.admin_dn, _ldap.admin_dn_password)
    except ldap.LDAPError as error:
        _logger.log('[' + __name__ + '] LDAP connection error: {}'.format(error),_logger.LogLevel.ERROR)
    try:
        result = ldap_conn.delete_s(dn)
        _logger.log('[' + __name__ + '] dn {0} deleted'.format(dn),_logger.LogLevel.INFO)
    except ldap.LDAPError as error:
        _logger.log('[' + __name__ + '] unable to delete dn {0}: {1}'.format(dn, error),_logger.LogLevel.ERROR)

    ldap_conn.unbind()


def purge_authgroups(dn, groups):

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
        mod_attrs = [ (ldap.MOD_REPLACE, attribute, str(value).encode('utf-8') ) ]

    try:
        result = ldap_conn.modify_s(dn, mod_attrs)
        _logger.log('[' + __name__ + '] dn {0} attribute {1} set to {2}'.format(dn, attribute, value),_logger.LogLevel.INFO)
    except ldap.LDAPError as error:
        _logger.log('[' + __name__ + '] unable to update dn {0} attribute {1}: {2}'.format(dn, attribute, error),_logger.LogLevel.ERROR)
    ldap_conn.unbind()

def ldap_adduser(dn, attributes):

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

    # add an attribute to an empty/multivalued attribute

    ldap_conn = ldap.initialize(_ldap.ldap_host, bytes_mode=False)
    try:
        ldap_conn.simple_bind_s(_ldap.admin_dn, _ldap.admin_dn_password)
    except ldap.LDAPError as error:
        _logger.log('[' + __name__ + '] LDAP connection error: {}'.format(error),_logger.LogLevel.ERROR)

    mod_attrs = [ (ldap.MOD_ADD, attribute, str(value).encode('utf-8') ) ]

    try:
        result = ldap_conn.modify_s(dn, mod_attrs)
        _logger.log('[' + __name__ + '] dn {0} attribute {1} set to {2}'.format(dn, attribute, value),_logger.LogLevel.INFO)
    except ldap.LDAPError as error:
        _logger.log('[' + __name__ + '] unable to update dn {0} attribute {1}: {2}'.format(dn, attribute, error),_logger.LogLevel.ERROR)
    ldap_conn.unbind()

def ldap_altupdate(function, main_charid, alt_charid):

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
