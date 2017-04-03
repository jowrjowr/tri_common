import asyncio
import common.database as _database
import common.logger as _logger
import MySQLdb as mysql

def audit_core():

    import json
    import common.request_esi

    # do the needful against a given charid

    _logger.log('[' + __name__ + '] auditing CORE',_logger.LogLevel.DEBUG)

    # get all tri service users

    try:
        sql_conn = mysql.connect(
            database=_database.DB_DATABASE,
            user=_database.DB_USERNAME,
            password=_database.DB_PASSWORD,
            host=_database.DB_HOST)
    except mysql.Error as err:
        _logger.log('[' + __name__ + '] mysql error: ' + str(err), _logger.LogLevel.ERROR)
        return False

    # the primary table is "Users", which everything else will key off of.
    # no entry in Users? you are gone.

    # the three tables we want to keep fully audited are:
    # Users (core users)
    # Teamspeak (ts3 users)
    # CrestTokens (SSO tokens)

    # there's a cost to having bullshit in those. other tables have separate auditing or are handled here.

    tables = [ 'CrestTokens', 'Users', 'Teamspeak' ]
    characters = dict()

    for table in tables:
        cursor = sql_conn.cursor()
        query = 'SELECT charID, charName from {0}'.format(table)
        try:
            count = cursor.execute(query)
            rows = cursor.fetchall()
        except Exception as err:
            _logger.log('[' + __name__ + '] mysql error: ' + str(err), _logger.LogLevel.ERROR)
            return
        finally:
            cursor.close()

        _logger.log('[' + __name__ + '] number of users in core table {0}: {1}'.format(table,str(count)), _logger.LogLevel.INFO)

        for row in rows:
            characters[row[0]] = row[1]

    sql_conn.close()

    # loop and audit each individual user, but do it async because there are lots

    loop = asyncio.new_event_loop()

    async def validate_loop(loop, characters):
        purgecount = 0
        for charid, charname in characters.items():
            task = loop.create_task(user_validate(charid, charname))
            result = await task
            if result == True:
                purgecount = purgecount + 1
        return purgecount

    purgecount = loop.run_until_complete(validate_loop(loop, characters))
    loop.close()

    _logger.log('[' + __name__ + '] number of users purged: {0}'.format(purgecount), _logger.LogLevel.INFO)

    return

async def user_validate(charid, charname):

    import common.database as _database
    import common.logger as _logger
    import MySQLdb as mysql
    import json

    import common.request_esi

    # is this character blue?
    esi_url = 'https://api.triumvirate.rocks/core/isblue?id=' + str(charid)

    # do the request, but catch exceptions for connection issues
    try:
        request = common.request_esi.esi(__name__, esi_url)
    except common.request_esi.NotHttp200 as error:
        if not error.code == 404:
            # something broke severely
            _logger.log('[' + __name__ + '] isblue API error ' + str(error.code) + ': ' + str(error.message), _logger.LogLevel.ERROR)
            return False
        # 404 simply means this was not found as a character (or my endpoint disappeared lol)
        return False

    result_parsed = json.loads(request)
    isblue = result_parsed['code']

    if isblue == 0:
        _logger.log('[' + __name__ + '] charid {0} ({1}) is reporting not blue.'.format(charid,charname),_logger.LogLevel.INFO)
    elif isblue == 1:
        return False
    else:
        _logger.log('[' + __name__ + '] nonsensical isblue result for charid {0} ({1}): {2}'.format(charid,charname,isblue),_logger.LogLevel.ERROR)
        return False

    try:
        sql_conn = mysql.connect(
            database=_database.DB_DATABASE,
            user=_database.DB_USERNAME,
            password=_database.DB_PASSWORD,
            host=_database.DB_HOST)
        cursor = sql_conn.cursor()
    except mysql.Error as err:
        _logger.log('[' + __name__ + '] mysql error: ' + str(err), _logger.LogLevel.ERROR)
        return False

    # now, the CCP ESI endpoint will sometimes return bullshit so a buffer for purging needs to be installed.
    # at this point, the user in question is reported not blue. so we'll increment the strike counter, then 
    # purge if necessary

    # increment the strike counter

    query = 'UPDATE Users SET strike = strike + 1 WHERE charID = %s'
    try:
        cursor.execute(query, (charid,))
    except mysql.Error as err:
        _logger.log('[' + __name__ + '] mysql error: ' + str(err), _logger.LogLevel.ERROR)
        return False

    # successful up until this point. commit.
    sql_conn.commit()

    query = 'SELECT strike FROM Users WHERE charID = %s'
    try:
        cursor.execute(query, (charid,))
        result = cursor.fetchone()
        if result == None:
            # this should never happen but was an edge case
            # created by testing some other things. injected bad data.
            strike = 100
        else:
            strike = int(result[0])
    except mysql.Error as err:
        _logger.log('[' + __name__ + '] mysql error: ' + str(err), _logger.LogLevel.ERROR)
        return False

    # three strikes and you are out.

    if strike <= 3:
        # no purge. yet.
        sql_conn.close()
        return False

    # here on, the user has had 3 isblue fails and is now getting purged

    _logger.log('[' + __name__ + '] charid {0} ({1}) has reported not blue {2} times. fully purging'.format(charid,charname,strike),_logger.LogLevel.INFO)

    # purge from relevant tables that key off charID
    # the SRP and Security tables are deliberately left out.

    tables = [
        'CrestTokens','SkillTraining',
        'Skills','SuperUsers','Teamspeak','Users','UsersSettings','sessions'
    ]


    for table in tables:
        query = 'DELETE FROM ' + table + ' WHERE charID = %s'
        try:
            row = cursor.execute(query, (charid,))
        except Exception as errmsg:
            _logger.log('[' + __name__ + '] mysql error: ' + str(errmsg), _logger.LogLevel.ERROR)
            return False
        _logger.log('[' + __name__ + '] charid {0} purged from table {1}'.format(charid, table), _logger.LogLevel.DEBUG)
    cursor.close()
    sql_conn.commit()
    sql_conn.close()
    _logger.log('[' + __name__ + '] user {0} removed from all tables'.format(charname),_logger.LogLevel.INFO)

    return True
