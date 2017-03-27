def maint_tokens():

    import common.logger as _logger
    import common.database as _database
    import common.maint.discord.refresh as _discordrefresh
    import MySQLdb as mysql
    import json
    import time

    _logger.log('[' + __name__ + '] refreshing tokens',_logger.LogLevel.INFO)

    try:
        sql_conn = mysql.connect(
            database=_database.DB_DATABASE,
            user=_database.DB_USERNAME,
            password=_database.DB_PASSWORD,
            host=_database.DB_HOST)
    except mysql.Error as err:
        _logger.log('[' + __name__ + '] mysql error: ' + str(err), _logger.LogLevel.ERROR)
        return

    cursor = sql_conn.cursor()
    now = time.time()

    # pick some cutoff that's really far so we refresh everything for now
    later = int(now) + 86400000

    query = 'SELECT id, refreshToken, TokenType FROM SpyTokens WHERE validUntil < %s'

    try:
        row = cursor.execute(query, (later,))
    except mysql.Error as err:
        _logger.log('[' + __name__ + '] mysql error: ' + str(err), _logger.LogLevel.ERROR)
        return
    _logger.log('[' + __name__ + '] Token count: {0}'.format(row), _logger.LogLevel.ERROR)

    rows = cursor.fetchall()
    cursor.close()
    # work with each individual token

    for row in rows:

        spy_id = int(row[0])
        old_rtoken = row[1].decode("utf-8")
        tokent = str(row[2])

        if tokent == 'discord':
            result = _discordrefresh.refresh_token(old_rtoken)
            print(result)
        try:
            atoken = result['access_token']
            rtoken = result['refresh_token']
            expires = result['expires_at']
        except TypeError:
            # dud token? not sure how to handle this yet
            print('busted token')
            print(result)
            continue

        cursor = sql_conn.cursor()
        query = 'UPDATE SpyTokens SET accessToken=%s, refreshToken=%s, validUntil=%s WHERE id=%s'
        try:
            row = cursor.execute(
                query, (
                    atoken,
                    rtoken,
                    expires,
                    spy_id,
                )
            )
        except Exception as errmsg:
            _logger.log('[' + __name__ + '] mysql error: ' + str(errmsg), _logger.LogLevel.ERROR)
            return('MySQL error :(')
        finally:
            cursor.close()

    # all the tokens are updated
    sql_conn.commit()
    sql_conn.close()
