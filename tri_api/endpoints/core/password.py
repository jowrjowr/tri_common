from flask import request
from tri_api import app

@app.route('/core/password/<charid>', methods=[ 'POST' ])
def core_password(charid):

    import json
    import ldap
    import ldap.modlist
    import common.logger as _logger
    import common.credentials.ldap as _ldap
    import common.ldaphelpers as _ldaphelpers
    import uuid
    import hashlib
    from flask import Response, request
    from passlib.hash import ldap_salted_sha1

    # reset password of charid

    ipaddress = request.headers['X-Real-Ip']
    log_charid = request.args.get('log_charid')    # logging purposes

    _logger.securitylog(__name__, 'reset password of charid {0}'.format(charid), ipaddress=ipaddress, charid=log_charid)


    # initialize connections

    try:
        ldap_conn = ldap.initialize(_ldap.ldap_host, bytes_mode=False)
        ldap_conn.simple_bind_s(_ldap.admin_dn, _ldap.admin_dn_password)
    except ldap.LDAPError as error:
        msg = 'LDAP connection error: {}'.format(error)
        _logger.log('[' + __name__ + '] {}'.format(msg),_logger.LogLevel.ERROR)
        js = json.dumps({ 'error': msg })
        return Response(js, status=500, mimetype='application/json')

    # find the user. partly to get the dn, partly to validate.

    dn = 'ou=People,dc=triumvirate,dc=rocks'
    filterstr='(uid={})'.format(charid)
    attrlist=['characterName', 'authGroup' ]
    code, result = _ldaphelpers.ldap_search(__name__, dn, filterstr, attrlist)

    if code == False:
        msg = 'unable to fetch ldap information: {}'.format(error)
        _logger.log('[' + __name__ + '] {}'.format(msg),_logger.LogLevel.ERROR)
        js = json.dumps({ 'error': msg })
        return Response(js, status=500, mimetype='application/json')


    if result == None:
        msg = 'charid {0} not in ldap'.format(charid)
        _logger.log('[' + __name__ + '] {}'.format(msg),_logger.LogLevel.ERROR)
        js = json.dumps({ 'error': msg })
        return Response(js, status=404, mimetype='application/json')


    (dn, info), = result.items()

    # new password

    password = uuid.uuid4().hex[:8]
    password_hash = ldap_salted_sha1.hash(password)
    password_hash = password_hash.encode('utf-8')

    mod_attrs = [ (ldap.MOD_REPLACE, 'userPassword', [password_hash] ) ]

    try:
        ldap_conn.modify_s(dn, mod_attrs)
    except ldap.LDAPError as error:
        msg = 'unable to modify password of {0}: {1}'.format(dn, error)
        _logger.log('[' + __name__ + '] {}'.format(msg),_logger.LogLevel.ERROR)
        js = json.dumps({ 'error': msg })
        return Response(js, status=500, mimetype='application/json')

    response = { 'password': password }
    return Response(json.dumps(response), status=200, mimetype='application/json')
