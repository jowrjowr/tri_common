from flask import request
from tri_api import app


@app.route('/characters', methods=['GET'])
def characters():
    from common.check_scope import check_scope
    from common.request_esi import esi
    from tri_core.common.scopes import scope
    from flask import Response, request
    from json import dumps
    from requests import get as requests_get

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

        # assume that the char id is main
        ldap_conn = ldap.initialize(_ldap.ldap_host, bytes_mode=False)

        try:
            ldap_conn.simple_bind_s(_ldap.admin_dn,
                                    _ldap.admin_dn_password)
        except ldap.LDAPError as error:
            _logger.log('[' + __name__ + '] LDAP connection error: {}'.format(error),
                        _logger.LogLevel.ERROR)
            raise

        try:
            mains = ldap_conn.search_s('ou=People,dc=triumvirate,dc=rocks', ldap.SCOPE_SUBTREE,
                                       filterstr='(&(objectclass=pilot)(uid={0}))'
                                       .format(char_id),
                                       attrlist=['uid', 'characterName', 'corporation', 'alliance', 'esiAccessToken'])

            users = ldap_conn.search_s('ou=People,dc=triumvirate,dc=rocks', ldap.SCOPE_SUBTREE,
                                       filterstr='(&(objectclass=pilot)(altOf={0}))'
                                       .format(char_id),
                                       attrlist=['uid', 'characterName', 'corporation', 'alliance', 'esiAccessToken'])
        except ldap.LDAPError as error:
            _logger.log('[' + __name__ + '] unable to fetch ldap users: {}'.format(error), _logger.LogLevel.ERROR)
            raise

        _logger.log('[' + __name__ + '] found {0} mains and {1} alts'.format(mains.__len__(), users.__len__()),
                    _logger.LogLevel.INFO)

        if mains.__len__() != 1:
            js = dumps({'error': 'no main character found for char_id={0}'.format(char_id)})
            return Response(js, status=404, mimetype='application/json')

        _, main_data = mains[0]

        json_dict = {'main': {}, 'alts': []}

        json_dict['main']['character_id'] = int(main_data['uid'][0].decode('utf-8'))
        json_dict['main']['character_name'] = main_data['characterName'][0].decode('utf-8')
        json_dict['main']['corporation_id'] = int(main_data['corporation'][0].decode('utf-8'))
        json_dict['main']['alliance_id'] = int(main_data['alliance'][0].decode('utf-8'))
        if 'esiAccessToken' in main_data:
            json_dict['main']['esi_token'] = True
            json_dict['main']['esi_token_valid'] = check_scope('acc_management',
                                                               charid=int(main_data['uid'][0].decode('utf-8')),
                                                               scopes=scope)[0]
        else:
            json_dict['main']['esi_token'] = False

        for user in users:
            _, alt_data = user

            new_entry = {}

            new_entry['main']['character_id'] = int(alt_data['uid'][0].decode('utf-8'))
            new_entry['main']['character_name'] = alt_data['characterName'][0].decode('utf-8')
            new_entry['main']['corporation_id'] = int(alt_data['corporation'][0].decode('utf-8'))
            new_entry['main']['alliance_id'] = int(alt_data['alliance'][0].decode('utf-8'))
            if 'esiAccessToken' in alt_data:
                new_entry['main']['esi_token'] = True
                new_entry['main']['esi_token_valid'] = check_scope('acc_management',
                                                                   charid=int(alt_data['uid'][0].decode('utf-8')),
                                                                   scopes=scope)[0]
            else:
                new_entry['main']['esi_token'] = False

            json_dict['alts'].append(new_entry)

        _logger.log('[' + __name__ + '] fetched characters successfully', _logger.LogLevel.INFO)

        js = dumps(json_dict)
        return Response(js, status=200, mimetype='application/json')
    except Exception as error:
        _logger.log('[' + __name__ + '] characters endpoint failed: {}'.format(error), _logger.LogLevel.ERROR)
        js = dumps({'error': str(error)})
        return Response(js, status=500, mimetype='application/json')


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
