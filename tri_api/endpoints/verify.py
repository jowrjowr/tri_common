from flask import request
from tri_api import app


@app.route('/verify', methods=['GET'])
def verify():
    from flask import Response, request
    from json import dumps

    import ldap.modlist
    import common.logger as _logger
    import common.credentials.ldap as _ldap

    try:
        if 'char_id' not in request.args:
            js = dumps({'error': 'no char_id supplied'})
            return Response(js, status=401, mimetype='application/json')

        try:
            char_id = int(request.args['char_id'])
        except ValueError:
            js = dumps({'error': 'char_id is not an integer'})
            return Response(js, status=401, mimetype='application/json')

        # get ldap entry
        ldap_conn = ldap.initialize(_ldap.ldap_host, bytes_mode=False)

        try:
            ldap_conn.simple_bind_s(_ldap.admin_dn,
                                    _ldap.admin_dn_password)
        except ldap.LDAPError as error:
            _logger.log('[' + __name__ + '] LDAP connection error: {}'.format(error),
                        _logger.LogLevel.ERROR)

        try:
            users = ldap_conn.search_s('ou=People,dc=triumvirate,dc=rocks', ldap.SCOPE_SUBTREE,
                                       filterstr='(&(objectclass=pilot)(uid={0}))'.format(char_id),
                                       attrlist=['uid', 'altOf'])
        except ldap.LDAPError as error:
            _logger.log('[' + __name__ + '] unable to fetch ldap users: {}'.format(error), _logger.LogLevel.ERROR)
            return

        if users.__len__() != 1:
            js = dumps({'error': 'char_id: {0} returned 0 or too many entries'.format(char_id)})
            return Response(js, status=404, mimetype='application/json')

        _, udata = users[0]

        if 'altOf' in udata:
            try:
                users = ldap_conn.search_s('ou=People,dc=triumvirate,dc=rocks', ldap.SCOPE_SUBTREE,
                                           filterstr='(&(objectclass=pilot)(uid={0}))'.format(udata['altOf']),
                                           attrlist=['uid'])
                _, udata = users[0]
            except ldap.LDAPError as error:
                _logger.log('[' + __name__ + '] unable to fetch ldap users: {}'.format(error), _logger.LogLevel.ERROR)
                return

        main_char_id = int(udata['uid'][0].decode('utf-8'))

        js = dumps({'character_id': main_char_id})
        return Response(js, status=200, mimetype='application/json')
    except Exception as error:
        js = dumps({'error': error})
        return Response(js, status=500, mimetype='application/json')
