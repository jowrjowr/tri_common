def maint_tokens():

    import common.logger as _logger
    import common.database as _database
    import common.maint.discord.refresh as _discordrefresh
    import common.maint.eve.refresh as _everefresh
    import MySQLdb as mysql
    import json
    import time
    import datetime

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

    # purge damaged tokens before i grab something i can't use

    query = 'DELETE FROM CrestTokens WHERE refreshToken IS NULL'

    try:
        row = cursor.execute(query,)
    except mysql.Error as err:
        _logger.log('[' + __name__ + '] mysql error: ' + str(err), _logger.LogLevel.ERROR)
        return

    # grab non-crippletokens
    # how do null refresh tokens even get installed?!

    query = 'SELECT charID, refreshToken FROM CrestTokens WHERE refreshToken IS NOT NULL'

    try:
        row = cursor.execute(query,)
    except mysql.Error as err:
        _logger.log('[' + __name__ + '] mysql error: ' + str(err), _logger.LogLevel.ERROR)
        return
    _logger.log('[' + __name__ + '] eve SSO token count: {0}'.format(row), _logger.LogLevel.INFO)

    rows = cursor.fetchall()

    cursor.close()
    # work with each individual token

    eve_broketokens = 0
    discord_broketokens = 0

    for row in rows:

        charid = int(row[0])
        old_rtoken = row[1].decode("utf-8")
        tokent = 'eve'

        # right now it's just the eve ESI tokens, but i'm leaving the multi-token
        # refresh machinery in place for when we do discord

        if tokent == 'discord':
            query = 'UPDATE SpyTokens SET accessToken=%s, refreshToken=%s, validUntil=%s WHERE id=%s'
            result = _discordrefresh.refresh_token(old_rtoken)
        if tokent == 'eve':
            query = 'UPDATE CrestTokens SET accessToken=%s, refreshToken=%s, validUntil=FROM_UNIXTIME(%s) WHERE charID=%s'
            result = _everefresh.refresh_token(old_rtoken)

        try:
            atoken = result['access_token']
            rtoken = result['refresh_token']
            expires = result['expires_at']
        except TypeError:
            # this token is busted. but there could be lots of reasons for it. do nothing.
            # if someone has a busted token their services don't work so they'll fix it
            #
            # or not. whichever.
            eve_broketokens = eve_broketokens + 1
            _logger.log('[' + __name__ + '] nonfunctional token for charid {0}: {1}'.format(charid, result), _logger.LogLevel.WARNING)
            continue

        cursor = sql_conn.cursor()
        try:
            row = cursor.execute(
                query, (
                    atoken,
                    rtoken,
                    expires,
                    charid,
                )
            )
        except Exception as errmsg:
            _logger.log('[' + __name__ + '] mysql error: ' + str(errmsg), _logger.LogLevel.ERROR)
            return('MySQL error :(')
        finally:
            cursor.close()
    _logger.log('[' + __name__ + '] eve token breakage count: {}'.format(eve_broketokens), _logger.LogLevel.INFO)

    # all the tokens are updated
    sql_conn.commit()
    sql_conn.close()
