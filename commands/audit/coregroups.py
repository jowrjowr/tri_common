def audit_coregroups():

    import common.logger as _logger
    import common.database as _database
    import MySQLdb as mysql

    _logger.log('[' + __name__ + '] auditing CORE groups',_logger.LogLevel.INFO)

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
    query = 'SELECT idGroups,GroupName,Members from Groups'
    try:
        cursor.execute(query)
    except Exception as err:
        _logger.log('[' + __name__ + '] mysql error: ' + str(err), _logger.LogLevel.ERROR)
        return

    rows = cursor.fetchall()
    cursor.close()
    sql_conn.close()

    # loop and audit each individual core group

    for row in rows:
        groupid = row[0]
        groupname = row[1]
        blob = row[2]
        if not blob == None:
            group_validate(groupid, groupname, blob)
    return

def group_validate(groupid, groupname, blob):

    import phpserialize
    import MySQLdb as mysql
    import copy
    import common.database as _database
    import common.logger as _logger

    group = []
    try:
        group = phpserialize.loads(blob)
    except ValueError as err:
        pass
    _logger.log('[' + __name__ + '] validating group {0}'.format(groupname),_logger.LogLevel.DEBUG)

    newgroup = copy.deepcopy(group)
    for key in group:
        userid = int(group[key])

        # core database crosschecking. sadly necessary.
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
        query = 'SELECT charID, charName from Users where charID = %s'

        try:
            count = cursor.execute(query, (userid,))
        except Exception as errmsg:
            _logger.log('[' + __name__ + '] mysql error: ' + str(errmsg), _logger.LogLevel.ERROR)
            return
        finally:
            cursor.close()
            sql_conn.close()

        # do not do any formal isblue() checks here. allow core auditing to do it, and then remove the user.
        # once the user is gone, the group can then be removed.

        if count == 0:
            _logger.log('[' + __name__ + '] removing charid {0} from group {1}'.format(userid,groupname),_logger.LogLevel.INFO)
            newgroup.pop(key, None)


    if group == newgroup:
        # nothing to do.
        return

    serial = phpserialize.serialize(newgroup)
    # re-serialize the data stucture and push it back into the database

    try:
        sql_conn = mysql.connect(
            database=_database.DB_DATABASE,
            user=_database.DB_USERNAME,
            password=_database.DB_PASSWORD,
            host=_database.DB_HOST)
    except mysql.Error as err:
        _logger.log('[' + __name__ + '] mysql error: ' + str(err), _logger.LogLevel.ERROR)
        return

    print(groupid)
    cursor = sql_conn.cursor()
    query = 'UPDATE Groups SET Members=%s WHERE idGroups=%s'
    try:
        cursor.execute(query, (serial,groupid,))
        _logger.log('[' + __name__ + '] Group "{1}" updated'.format(userid,groupname),_logger.LogLevel.DEBUG)
        sql_conn.commit()
    except Exception as err:
        _logger.log('[' + __name__ + '] mysql error: ' + str(err), _logger.LogLevel.ERROR)
        return
    finally:
        cursor.close()
        sql_conn.close()
    return

