def maint_discordusers():

    import common.logger as _logger
    import logging
    import common.database as _database
    import common.credentials.discord as _discord
    from common.discord_api import discord_allmembers
    import MySQLdb as mysql
    import warnings

    # setup logging

    _logger.log('[' + __name__ + '] storing discord user info',_logger.LogLevel.INFO)
    logging.getLogger("discord").setLevel(logging.ERROR)

    # setup mysql

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

    # setup the discord database now that we have the spies

    sql_conn.select_db('discord')
    warnings.filterwarnings('error', category=mysql.Warning)

    for covername, username, password in rows:

        member_info = discord_allmembers(__name__, 'user', user=(username, password))

        for server in member_info:

            # make sure the mysql table for the server user data exists

            table = 'users_{0}'.format(server)

            query = 'CREATE TABLE IF NOT EXISTS {0} ('.format(table)
            query += 'member_id bigint(8), bot int(1), display_name varchar(256), '
            query += 'server_name varchar(256), discriminator smallint(4), joined_at timestamp, '
            query += 'status varchar(256), member_nick varchar(256), top_role varchar(256), server_permissions int(16))'
            query += ' CHARACTER SET utf8mb4'

            try:
                result = cursor.execute(query)

            except mysql.Warning as err:
                # nobody cares if the table exists already
                _logger.log('[' + __name__ + '] mysql warning: ' + str(err), _logger.LogLevel.DEBUG)
            except Exception as err:
                _logger.log('[' + __name__ + '] mysql error: ' + str(err), _logger.LogLevel.ERROR)
                continue

            users = member_info[server]

            # loop through the users and store the data

            for user in users:

                # insert each data

                query = 'REPLACE INTO {0} ('.format(table)
                query += 'member_id, bot, display_name, server_name, discriminator, '
                query += 'joined_at, status, member_nick, top_role, server_permissions '
                query += ') VALUES (%s, %s, %s, %s, %s, FROM_UNIXTIME(%s), %s, %s, %s, %s)'

                try:
                    cursor.execute(query, (
                        user['id'],
                        user['bot'],
                        user['display_name'],
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
                finally:
                    sql_conn.commit()
    sql_conn.close()
