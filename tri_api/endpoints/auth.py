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

        ldap_conn = ldap.initialize(_ldap.ldap_host, bytes_mode=False)

        try:
            ldap_conn.simple_bind_s(_ldap.admin_dn,
                                    _ldap.admin_dn_password)
        except ldap.LDAPError as error:
            _logger.log('[' + __name__ + '] LDAP connection error: {}'.format(error),
                        _logger.LogLevel.ERROR)
            raise

        try:
            users = ldap_conn.search_s('ou=People,dc=triumvirate,dc=rocks', ldap.SCOPE_SUBTREE,
                                       filterstr='(&(objectclass=pilot)(uid={0}))'.format(char_id),
                                       attrlist=['uid', 'altOf', 'characterName'])
        except ldap.LDAPError as error:
            _logger.log('[' + __name__ + '] unable to fetch ldap users: {}'.format(error), _logger.LogLevel.ERROR)
            raise

        if users.__len__() != 1:
            js = dumps({'error': 'char_id={0} returned no or too many entries'.format(char_id)})
            return Response(js, status=404, mimetype='application/json')

        _, udata = users[0]

        if 'altOf' in udata:
            try:
                users = ldap_conn.search_s('ou=People,dc=triumvirate,dc=rocks', ldap.SCOPE_SUBTREE,
                                           filterstr='(&(objectclass=pilot)(uid={0}))'.format(udata['altOf'][0].decode('utf-8')),
                                           attrlist=['uid', 'altOf', 'characterName'])

                _logger.log('[' + __name__ + '] user length: {0} [{1}]'.format(users.__len__(), users),
                            _logger.LogLevel.INFO)

                if users.__len__() != 1:
                    js = dumps({'error': 'char_id: {0} is altOf {1} which is not registered'.format(char_id, udata['altOf'])})
                    return Response(js, status=404, mimetype='application/json')

                _, udata = users[0]
            except ldap.LDAPError as error:
                _logger.log('[' + __name__ + '] unable to fetch ldap users: {}'.format(error), _logger.LogLevel.ERROR)
                raise

        main_char_id = int(udata['uid'][0].decode('utf-8'))
        main_char_name = udata['characterName'][0].decode('utf-8')

        js = dumps({
            'character_id': main_char_id,
            'character_name': main_char_name
        })
        return Response(js, status=200, mimetype='application/json')
    except Exception as error:
        js = dumps({'error': str(error)})
        return Response(js, status=500, mimetype='application/json')

@app.route('/token', methods=['GET'])
def register_token():
    from tri_core.common.register import registeruser
    from flask import Response, request
    from json import dumps

    try:
        if 'char_id' not in request.args:
            js = dumps({'error': 'no char_id supplied'})
            return Response(js, status=401, mimetype='application/json')

        if 'main_id' not in request.args:
            js = dumps({'error': 'no main_id supplied'})
            return Response(js, status=401, mimetype='application/json')


        if 'atoken' not in request.args:
            js = dumps({'error': 'no access_token supplied'})
            return Response(js, status=401, mimetype='application/json')

        if 'rtoken' not in request.args:
            js = dumps({'error': 'no refresh_token supplied'})
            return Response(js, status=401, mimetype='application/json')

        try:
            char_id = int(request.args['char_id'])
            main_id = int(request.args['main_id'])

            access_token = request.args['atoken']
            refresh_token = request.args['rtoken']
        except ValueError:
            js = dumps({'error': 'char_id or main_id is not an integer'})
            return Response(js, status=401, mimetype='application/json')

        if char_id == main_id:
            is_alt = False
        else:
            is_alt = True

        code, result = registeruser(char_id, access_token, refresh_token, is_alt, main_id)

        if code == False:
            js = dumps({'error': 'failed to register char {0}'.format(char_id)})
            return Response(js, status=500, mimetype='application/json')

        return  Response(dumps({}), status=200, mimetype='application/json')
    except Exception as error:
        js = dumps({'error': str(error)})
        return Response(js, status=500, mimetype='application/json')