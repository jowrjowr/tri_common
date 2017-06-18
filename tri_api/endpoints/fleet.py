from flask import request
from tri_api import app


@app.route('/fleets', methods=['GET'])
def fleets():
    import common.database as _database
    from common.check_scope import check_scope
    from common.request_esi import esi
    from tri_core.common.scopes import scope
    from flask import Response, request
    from json import dumps
    from requests import get as requests_get

    import ldap.modlist
    import common.logger as _logger
    import common.credentials.ldap as _ldap
    import MySQLdb as mysql



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
            users = ldap_conn.search_s('ou=People,dc=triumvirate,dc=rocks', ldap.SCOPE_SUBTREE,
                                       filterstr='(&(objectclass=pilot)(uid={0}))'
                                       .format(char_id),
                                       attrlist=['authGroup'])
        except ldap.LDAPError as error:
            _logger.log('[' + __name__ + '] unable to fetch ldap users: {}'.format(error), _logger.LogLevel.ERROR)
            raise

        if users.__len__() != 1:
            js = dumps({'error': 'no main character found for char_id={0}'.format(char_id)})
            return Response(js, status=404, mimetype='application/json')

        _, udata = users[0]
        groups = [g.decode('utf-8') for g in udata['authGroup']]

        # the mysql way
        try:
            sql_conn = mysql.connect(
                database=_database.DB_DATABASE,
                user=_database.DB_USERNAME,
                password=_database.DB_PASSWORD,
                host=_database.DB_HOST)
            cursor = sql_conn.cursor()
        except mysql.Error as err:
            _logger.log('[' + __name__ + '] mysql error: ' + str(err), _logger.LogLevel.ERROR)
            raise

        query = "SELECT Time, FC, FormUP, Type, authgroup FROM OpsBoard WHERE Time >= CURTIME() ORDER BY Time"

        try:
            cursor.execute(query)

            fleets = []

            for (time, fc, form_up, type, auth) in cursor:
                fleet = {}

                fleet['time_short'] = time.strftime("%H%MET %m-%d")
                fleet['time_long'] = time.strftime("%H:%M %Y-%m-%d")

                fleet['fc'] = fc
                if form_up is None or form_up == '':
                    fleet['form_up'] = "N/A"
                else:
                    fleet['form_up'] = form_up

                if type == "THIRD PARTY FIGHT":
                    type = "FLEET"

                fleet['type'] = type

                if auth is None or auth == '':
                    fleet['auth_group'] = 'vanguard'
                else:
                    fleet['auth_group'] = auth

                if fleet['auth_group'] in groups:
                    fleets.append(fleet)
        except Exception as errmsg:
            _logger.log('[' + __name__ + '] mysql error: ' + str(errmsg), _logger.LogLevel.ERROR)
            raise
        finally:
            cursor.close()
            sql_conn.commit()
            sql_conn.close()

        js = dumps(fleets)
        return Response(js, status=200, mimetype='application/json')
    except Exception as error:
        js = dumps({'error': str(error)})
        return Response(js, status=500, mimetype='application/json')
