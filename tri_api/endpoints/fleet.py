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

        query = "SELECT (Time, FC, FormUP, Type, authgroup) FROM OpsBoard WHERE Time >= CURDATE() ORDER BY Time"

        try:
            row = cursor.execute(
                query
            )
        except Exception as errmsg:
            _logger.log('[' + __name__ + '] mysql error: ' + str(errmsg), _logger.LogLevel.ERROR)
            raise
        finally:
            cursor.close()
            sql_conn.commit()
            sql_conn.close()

        for fleet in row:
            if fleet[4] is None:
                fleet[4] = 'vanguard'


        js = dumps([{'time': fleet[0],
                     'fc': fleet[1],
                     'form_up': fleet[2],
                     'type': fleet[3],
                     'auth_group': fleet[4]} for fleet in row])

        return Response(js, status=200, mimetype='application/json')
    except Exception as error:
        js = dumps({'error': str(error)})
        return Response(js, status=500, mimetype='application/json')
