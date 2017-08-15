def maint_discordusers():

    import common.logger as _logger
    import redis
    import logging
    import common.database as _database
    import common.credentials.discord as _discord
    from common.discord_api import discord_allmembers
    import MySQLdb as mysql
    import warnings
    import re

    # setup logging

    _logger.log('[' + __name__ + '] storing discord user info',_logger.LogLevel.INFO)
    logging.getLogger("discord").setLevel(logging.ERROR)

    # setup connections

    r = redis.StrictRedis(host='localhost', port=6379, db=0)
    try:
        r.client_list()
    except redis.exceptions.ConnectionError as err:
        _logger.log('[' + __name__ + '] Redis connection error: ' + str(err), _logger.LogLevel.ERROR)
    except redis.exceptions.ConnectionRefusedError as err:
        _logger.log('[' + __name__ + '] Redis connection error: ' + str(err), _logger.LogLevel.ERROR)
    except Exception as err:
        logger.error('[' + __name__ + '] Redis generic error: ' + str(err))

    try:
        sql_conn = mysql.connect(
            database=_database.DB_DATABASE,
            user=_database.DB_USERNAME,
            password=_database.DB_PASSWORD,
            host=_database.DB_HOST,
            charset='utf8mb4',
        )
    except mysql.Error as err:
        _logger.log('[' + __name__ + '] mysql error: ' + str(err), _logger.LogLevel.ERROR)
        return False

    # get all the discords spies have access to
    # this will include friendly discords

    cursor = sql_conn.cursor()
    query = 'SELECT covername, username, password FROM Spies where server_type = %s'
    try:
        count = cursor.execute(query, ('discord',))
        rows = cursor.fetchall()
    except Exception as err:
        _logger.log('[' + __name__ + '] mysql error: ' + str(err), _logger.LogLevel.ERROR)
        return

    # fetch each table from discord so we know what is/was being tracked

    sql_conn.select_db('information_schema')
    query = 'SELECT TABLE_NAME FROM TABLES WHERE TABLE_SCHEMA=%s'

    try:
        cursor.execute(query, ('discord',))
        tables = cursor.fetchall()
    except Exception as err:
        _logger.log('[' + __name__ + '] mysql error: ' + str(err), _logger.LogLevel.ERROR)
        return

    discords = set()

    regex = r'^users_(\S+)$'
    for table, in tables:
        match = re.match(regex, table)

        if match: discords.add(match.group(1))

    # setup the discord database now that we have the spies

    sql_conn.select_db('discord')
    sql_conn.autocommit(False)
    warnings.filterwarnings('error', category=mysql.Warning)
    cursor.close()

    for covername, username, password in rows:
        member_info = discord_allmembers(__name__, 'user', user=(username, password))

        for server in member_info:

            cursor = sql_conn.cursor()

            # get or set the discord name

            try:
                server_name = r.get(server)
                server_name = server_name.decode('utf-8')
            except Exception as err:
                server_name = None

            #print(server, server_name)
            # remove this discord from the list

            discords.discard(server)

            # make sure the mysql table for the server user data exists

            table = 'users_{0}'.format(server)


            query = 'CREATE TABLE IF NOT EXISTS {0} ('.format(table)
            query += 'member_id bigint(8) NOT NULL PRIMARY KEY, bot int(1), username varchar(256), '
            query += 'server_name varchar(256), discriminator smallint(4), joined_at timestamp, '
            query += 'status varchar(256), member_nick varchar(256), top_role varchar(256), server_permissions int(16)'
            query += ' )'
            query += ' CHARACTER SET utf8mb4'

            try:
                result = cursor.execute(query)

            except mysql.Warning as err:
                # nobody cares if the table exists already
                _logger.log('[' + __name__ + '] mysql warning: ' + str(err), _logger.LogLevel.DEBUG)
            except Exception as err:
                _logger.log('[' + __name__ + '] mysql error: ' + str(err), _logger.LogLevel.ERROR)
                continue

#            cursor.execute('drop table {}'.format(table))
#            continue
            users = member_info[server]

            # loop through the users and store the data

            for user in users:

                # store the server name

                if server_name == None:
                    try:
                        r.set(server, user['server_name'])
                    except Exception as err:
                        _logger.log('[' + __name__ + '] Redis error: ' + str(err), _logger.LogLevel.ERROR)

                # insert each data

                query = 'REPLACE INTO {0} ('.format(table)
                query += 'member_id, bot, username, server_name, discriminator, '
                query += 'joined_at, status, member_nick, top_role, server_permissions '
                query += ') VALUES (%s, %s, %s, %s, %s, FROM_UNIXTIME(%s), %s, %s, %s, %s)'

                try:
                    cursor.execute(query, (
                        user['id'],
                        user['bot'],
                        user['name'],
                        user['server_name'],
                        user['discriminator'],
                        user['joined_at'],
                        user['status'],
                        user['member_nick'],
                        user['top_role'],
                        user['server_permissions'],
                    ))
                except Exception as err:
                    _logger.log('[' + __name__ + '] mysql error: ' + str(err), _logger.LogLevel.ERROR)
            cursor.close()
            sql_conn.commit()
    sql_conn.close()

    if len(discords) == 0:
        return

    for discord in discords:

        try:
            server_name = r.get(discord)
            server_name = server_name.decode('utf-8')
        except Exception as e:
            server_name = server

        msg = 'lost access to discord {0}'.format(server)
        _logger.log('[' + __name__ + '] {0}'.format(msg), _logger.LogLevel.WARNING)
