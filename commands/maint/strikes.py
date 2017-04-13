def reset_strikes():

    import MySQLdb as mysql
    import common.database as _database
    import common.logger as _logger
    
    _logger.log('[' + __name__ + '] resetting user purge strike counts',_logger.LogLevel.INFO)
    
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
    
    query = 'UPDATE Users SET strike = 0'
    try:
        cursor.execute(query)
    except Exception as errmsg:
        _logger.log('[' + __name__ + '] mysql error: ' + str(errmsg), _logger.LogLevel.ERROR)
        return False
    finally:
        cursor.close()
        sql_conn.commit()
        sql_conn.close()
    _logger.log('[' + __name__ + '] user purge strike counts reset',_logger.LogLevel.INFO)
    return True
