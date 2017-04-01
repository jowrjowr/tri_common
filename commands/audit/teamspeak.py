import asyncio

def audit_teamspeak():

    import common.database as _database
    import common.jabber as _jabber
    import common.ts3 as _ts3
    import common.logger as _logger

    import logging
    import requests
    import json
    import ts3

    import common.request_esi

    _logger.log('[' + __name__ + '] auditing teamspeak',_logger.LogLevel.DEBUG)
    logging.getLogger("requests").setLevel(logging.WARNING)

    # http://py-ts3.readthedocs.io/en/latest/

    try:
        # Note, that the client will wait for the response and raise a
        # **TS3QueryError** if the error id of the response is not 0.
        ts3conn = ts3.query.TS3Connection(_ts3.TS_HOST)
        ts3conn.login(
            client_login_name=_ts3.TS_USER,
            client_login_password=_ts3.TS_PASSWORD
        )
    except ts3.query.TS3QueryError as err:
        _logger.log('[' + __name__ + '] unable to connect to TS3: {0}'.format(err.resp.error["msg"]),_logger.LogLevel.ERROR)
        return


    ts3conn.use(sid=_ts3.TS_SERVER_ID)

    # ts3 errorhandling is goofy.
    # if it can't find the user, it raises an error so we'll just assume failure means no user
    # and continue


    # it turns out clientdblist() are just users who are online or something.
    # this does not audit users-within-groups apparently

    try:
        resp = ts3conn.clientdblist()
    except ts3.query.TS3QueryError as err:
        _logger.log('[' + __name__ + '] ts3 error: {0}'.format(err),_logger.LogLevel.WARNING)

    loop = asyncio.new_event_loop()

    for user in resp.parsed:
        serviceuser = user['client_nickname']
        _logger.log('[' + __name__ + '] Validating ts3 user {0}'.format(serviceuser),_logger.LogLevel.DEBUG)

        # not really proper clients, so don't do anything

        if serviceuser == 'ServerQuery Guest':
            pass
        elif serviceuser == 'sovereign':
            pass
        else:
            # otherwise:

            ts3_userid = user['cldbid']
            loop.run_until_complete(user_validate(ts3_userid))


    # iterate through ts3 groups and validate assigned users

    try:
        resp = ts3conn.servergrouplist()
    except ts3.query.TS3QueryError as err:
        _logger.log('[' + __name__ + '] ts3 error: {0}'.format(err),_logger.LogLevel.WARNING)

    for group in resp.parsed:
        groupname = group['name']
        groupid = group['sgid']
        _logger.log('[' + __name__ + '] Validating ts3 group ({0}) {1}'.format(groupid, groupname),_logger.LogLevel.DEBUG)
        loop.run_until_complete(group_validate(groupid))

    loop.close()
    return ''


async def group_validate(ts3_groupid):

    # iterate through a given ts3 group and validate each individual userid
    import common.ts3 as _ts3
    import common.logger as _logger

    import logging
    import requests
    import json
    import time
    import ts3
    import asyncio

    # do not validate certain group ids
    # gid 8: guest

    skip = [ '8' ]

    for skip_id in skip:
        if skip_id == ts3_groupid:
            return

    try:
        # Note, that the client will wait for the response and raise a
        # **TS3QueryError** if the error id of the response is not 0.
        ts3conn = ts3.query.TS3Connection(_ts3.TS_HOST)
        ts3conn.login(
            client_login_name=_ts3.TS_USER,
            client_login_password=_ts3.TS_PASSWORD
        )
    except ts3.query.TS3QueryError as err:
        _logger.log('[' + __name__ + '] unable to connect to TS3: {0}'.format(err.resp.error["msg"]),_logger.LogLevel.ERROR)
        return

    ts3conn.use(sid=_ts3.TS_SERVER_ID)

    try:
        resp = ts3conn.servergroupclientlist(sgid=ts3_groupid)
    except ts3.query.TS3QueryError as err:
        _logger.log('[' + __name__ + '] ts3 error: {0}'.format(err),_logger.LogLevel.WARNING)

    loop = asyncio.get_event_loop()

    for user in resp.parsed:
        user_id = user['cldbid']
        loop.run_until_complete(user_validate(user_id))

async def user_validate(ts3_userid):

    # validate a given user against the core database
    import MySQLdb as mysql
    import common.database as _database
    import common.ts3 as _ts3
    import common.logger as _logger

    import logging
    import requests
    import json
    import time
    import ts3

    # do not validate certain user ids
    # uid 1: admin
    skip = [ '1' ]

    for skip_id in skip:
        if skip_id == ts3_userid:
            return
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
    query = 'SELECT ClientDBID,charName FROM Teamspeak WHERE ClientDBID = %s'

    try:
        activecount = cursor.execute(query, (ts3_userid,))
        if activecount == 0:
            registered_username = None
        else:
            registered_username = cursor.fetchone()[1]
    except Exception as errmsg:
        _logger.log('[' + __name__ + '] mysql error: ' + str(errmsg), _logger.LogLevel.ERROR)
        return False
    finally:
        cursor.close()
        sql_conn.close()


    try:
        # Note, that the client will wait for the response and raise a
        # **TS3QueryError** if the error id of the response is not 0.
        ts3conn = ts3.query.TS3Connection(_ts3.TS_HOST)
        ts3conn.login(
            client_login_name=_ts3.TS_USER,
            client_login_password=_ts3.TS_PASSWORD
        )
    except ts3.query.TS3QueryError as err:
        _logger.log('[' + __name__ + '] unable to connect to TS3: {0}'.format(err.resp.error["msg"]),_logger.LogLevel.ERROR)
        return

    ts3conn.use(sid=_ts3.TS_SERVER_ID)
    try:
        resp = ts3conn.clientlist()
        clients = resp.parsed
    except ts3.query.TS3QueryError as err:
        _logger.log('[' + __name__ + '] ts3 error: "{0}"'.format(err),_logger.LogLevel.WARNING)

    try:
        resp = ts3conn.clientdbinfo(cldbid=ts3_userid)
        user = resp.parsed
    except ts3.query.TS3QueryError as err:
        _logger.log('[' + __name__ + '] ts3 (uid: {0}) error: "{1}"'.format(ts3_userid, err),_logger.LogLevel.WARNING)


    user_nick = user[0]['client_nickname']
    user_lastip = user[0]['client_lastip']
    user_lastconn = int(user[0]['client_lastconnected'])
    user_conns = int(user[0]['client_totalconnections'])
    user_created = int(user[0]['client_totalconnections'])

    # if the user is online, we want to make sure that the username matches
    # what is in the teamspeak table

    for client in clients:
        clid = client['clid']
        cldbid = client['client_database_id']
        client_username = client['client_nickname']
        if cldbid == ts3_userid and client_username != registered_username:
            # online user has a username that does not match records.
            # "encourage" fixing this.
            reason = 'Please use your main character name as your teamspeak nickname, without any tags'
            try:
                resp = ts3conn.clientkick(reasonid=5, reasonmsg=reason, clid=clid)
                _logger.log('[' + __name__ + '] ts3 user {0} kicked from server: mismatch'.format(user_nick),_logger.LogLevel.WARNING)
                _logger.log('[' + __name__ + '] TS db: "{0}", client: "{1}"'.format(registered_username,client_username),_logger.LogLevel.WARNING)
            except ts3.query.TS3QueryError as err:
                _logger.log('[' + __name__ + '] ts3 error: "{0}"'.format(err),_logger.LogLevel.WARNING)


    if activecount == 1:
        # a nonzero return means the ts3 user is linked to an active core user
        #
        # we're done auditing this user. the user has a core entry and the correct
        # username he registered with.
        return

    # oops orphan. we hate orphans.
    # log the shit out of the orphan user

    lastconnected = time.gmtime(user_lastconn)
    lastconnected_iso = time.strftime("%Y-%m-%dT%H:%M:%S", lastconnected)
    created = time.gmtime(user_created)
    created_iso = time.strftime("%Y-%m-%dT%H:%M:%S", created)
    _logger.log('[' + __name__ + '] Orphan ts3 user: {0}'.format(user_nick), _logger.LogLevel.WARNING)
    _logger.log('[' + __name__ + '] User {0} created: {1}, last login: {2}, last ip: {3}, total connections: {4}'.format(
        user_nick,created_iso,lastconnected_iso,user_lastip,user_conns
    ), _logger.LogLevel.WARNING)


    # remove orphan ts3 users

    # first kick from the server if they are on, asking them to re-register
    # to do that i need the client id, which is not the client db id, because
    # of fucking course it isn't

    for client in clients:
        clid = client['clid']
        cldbid = client['client_database_id']
        if cldbid == ts3_userid:
            try:
                reason = 'You are detached from CORE. Please configure services.'
                resp = ts3conn.clientkick(reasonid=5, reasonmsg=reason, clid=clid)
                _logger.log('[' + __name__ + '] ts3 user {0} kicked from server (orphan user)'.format(user_nick),_logger.LogLevel.WARNING)
            except ts3.query.TS3QueryError as err:
                _logger.log('[' + __name__ + '] ts3 error: "{0}"'.format(err),_logger.LogLevel.WARNING)

    # now remove the client from the ts3 database

    try:
        resp = ts3conn.clientdbdelete(cldbid=ts3_userid)
        _logger.log('[' + __name__ + '] ts3 user {0} removed'.format(user_nick),_logger.LogLevel.WARNING)
    except ts3.query.TS3QueryError as err:
        _logger.log('[' + __name__ + '] ts3 error: "{0}"'.format(err),_logger.LogLevel.WARNING)

    # client removed. gg.

    return
