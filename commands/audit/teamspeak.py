import asyncio

def audit_teamspeak():

    import common.credentials.ts3 as _ts3
    import common.logger as _logger

    import ts3

    # invididual tasks for teamspeak
    # http://py-ts3.readthedocs.io/en/latest/

    _logger.log('[' + __name__ + '] auditing teamspeak',_logger.LogLevel.INFO)

    # ts3 errorhandling is goofy.
    # if it can't find the user, it raises an error so we'll just assume failure means no user
    # and continue

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

    ts3_logs(ts3conn)
    ts3_monitoring(ts3conn)
    ts3_validate_users(ts3conn)
    ts3_validate_groups(ts3conn)

def ts3_logs(ts3conn):

    import common.credentials.ts3 as _ts3
    import common.logger as _logger
    import common.credentials.ldap as _ldap

    import ts3
    import time
    import re

    # parse ts3 server logs and dump useful things into security log

    # we start from a zero position and work our way back to a checkpoint in the log

    position = 1
    stop = False
    logcount = -1 #off-by-one because i inject a line

    while position > 0 and stop == False:
        # a small position offset so i can start/stop cleanly
        if position == 1:
            position = 0

        try:
            resp = ts3conn.logview(lines=100, reverse=1, begin_pos=position)
        except ts3.query.TS3QueryError as err:
            _logger.log('[' + __name__ + '] ts3 error: {0}'.format(err),_logger.LogLevel.ERROR)
        for line in resp.parsed:
            if 'last_pos' in line.keys():
                file_size = line['file_size']
                last_pos = line['last_pos']
                position = int(last_pos)
                _logger.log('[' + __name__ + '] ts3 log size: {0}, last position: {1}'.format(file_size, last_pos),_logger.LogLevel.DEBUG)
            if 'l' in line.keys():
                logcount += 1
                entry = line['l']
                # parse the log
                date, level, target, server, logline = entry.split('|', 4)

                # stop processing logs as this is where we last were
                if logline == 'checkpoint':
                    stop = True
                    position = 0
                    break

                # convert the date into epoch

                # example date: 2017-05-13 14:34:58.223587

                date = time.strptime(date, "%Y-%m-%d %H:%M:%S.%f")
                date = time.mktime(date)

                # regex out login events

                # example line:
                # client connected 'Sightless 1'(id:1615) from 135.23.200.132:50743

                loginmatch = re.match( r"^client connected \'(.*)\'\(id:(.*)\) from (.*):(.*)$", logline, re.M)
                if loginmatch:
                    charname = loginmatch.group(1)
                    clientid = loginmatch.group(2)
                    ip = loginmatch.group(3)

                    # dump the result into the security log
                    _logger.securitylog(__name__, 'ts3 login', charname=charname, ipaddress=ip, date=date)


    _logger.log('[' + __name__ + '] new ts3 log entries: {0}'.format(logcount),_logger.LogLevel.INFO)

    # add index to log file
    try:
        resp = ts3conn.logadd(loglevel=4, logmsg='checkpoint')
    except ts3.query.TS3QueryError as err:
        _logger.log('[' + __name__ + '] ts3 error: {0}'.format(err),_logger.LogLevel.ERROR)


def ts3_monitoring(ts3conn):

    from common.graphite import sendmetric
    import common.credentials.ts3 as _ts3
    import common.logger as _logger

    import ts3

    # server statistics/information
    # might as well log some useful shit

    try:
        resp = ts3conn.serverrequestconnectioninfo()
    except ts3.query.TS3QueryError as err:
        _logger.log('[' + __name__ + '] ts3 error: {0}'.format(err),_logger.LogLevel.ERROR)
        return

    for stat in resp.parsed[0]:
        sendmetric(__name__, 'ts3', 'server_stats', stat, resp.parsed[0][stat])

    try:
        resp = ts3conn.serverinfo()
    except ts3.query.TS3QueryError as err:
        _logger.log('[' + __name__ + '] ts3 error: {0}'.format(err),_logger.LogLevel.ERROR)
        return

    # useful metrics as per the ts3 server query guide
    
    metrics = [ 'connection_bandwidth_sent_last_minute_total', 'connection_bandwidth_received_last_minute_total', ]

    for metric in metrics:
        sendmetric(__name__, 'ts3', 'vserver_{}'.format(_ts3.TS_SERVER_ID), metric, resp.parsed[0][metric])

    # log settings

    # need to ensure that the TS3 server has the logging settings desired, since there's
    # nothing in the ini that lets you set this information

    # this can be pivoted to managing settings as well

    # they come out as str() rather than int()
    logsettings = dict()
    logsettings['virtualserver_log_channel'] = int(resp.parsed[0]['virtualserver_log_channel'])
    logsettings['virtualserver_log_permissions'] = int(resp.parsed[0]['virtualserver_log_permissions'])
    logsettings['virtualserver_log_filetransfer'] = int(resp.parsed[0]['virtualserver_log_filetransfer'])
    logsettings['virtualserver_log_query'] = int(resp.parsed[0]['virtualserver_log_query'])
    logsettings['virtualserver_log_client'] = int(resp.parsed[0]['virtualserver_log_client'])
    logsettings['virtualserver_log_server'] = int(resp.parsed[0]['virtualserver_log_server'])

    for setting in logsettings:
        if logsettings[setting] == 0:
            _logger.log('[' + __name__ + '] ts3 log option {0} disabled'.format(setting),_logger.LogLevel.WARNING)

def ts3_validate_users(ts3conn):

    import common.logger as _logger
    import ts3

    # validate ts3 online users

    # skip these users
    skip = [ 'ServerQuery Guest', 'sovereign' ]

    # it turns out clientdblist() are just users who are online, rather than ALL users or something
    # this does not audit users-within-groups apparently
    try:
        resp = ts3conn.clientdblist()
    except ts3.query.TS3QueryError as err:
        _logger.log('[' + __name__ + '] ts3 error: {0}'.format(err),_logger.LogLevel.ERROR)
        return


    loop = asyncio.new_event_loop()

    for user in resp.parsed:
        serviceuser = user['client_nickname']
        if serviceuser in skip:
            # we don't want to waste time on internal users
            continue
        _logger.log('[' + __name__ + '] Validating ts3 user {0}'.format(serviceuser),_logger.LogLevel.DEBUG)
        ts3_userid = user['cldbid']
        loop.run_until_complete(user_validate(ts3_userid))

    return loop.close()

def ts3_validate_groups(ts3conn):

    import common.logger as _logger
    import ts3

    # iterate through ts3 groups and validate assigned users

    # don't validate certain groups:
    skip = [ '8' ]

    loop = asyncio.new_event_loop()

    try:
        resp = ts3conn.servergrouplist()
    except ts3.query.TS3QueryError as err:
        _logger.log('[' + __name__ + '] ts3 error: {0}'.format(err),_logger.LogLevel.ERROR)
        return

    for group in resp.parsed:
        groupname = group['name']
        groupid = group['sgid']
        if groupid in skip:
            continue
        _logger.log('[' + __name__ + '] Validating ts3 group ({0}) {1}'.format(groupid, groupname),_logger.LogLevel.DEBUG)
        loop.run_until_complete(group_validate(groupid))

    return loop.close()



async def group_validate(ts3_groupid):

    # iterate through a given ts3 group and validate each individual userid
    import common.credentials.ts3 as _ts3
    import common.logger as _logger

    import ts3
    import asyncio

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
        _logger.log('[' + __name__ + '] ts3 error: {0}'.format(err),_logger.LogLevel.ERROR)

    loop = asyncio.get_event_loop()

    for user in resp.parsed:
        user_id = user['cldbid']
        loop.run_until_complete(user_validate(user_id))

async def user_validate(ts3_userid):

    # validate a given user against the core database
    import MySQLdb as mysql
    import common.credentials.database as _database
    import common.credentials.ts3 as _ts3
    import common.logger as _logger

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
        _logger.log('[' + __name__ + '] ts3 error: "{0}"'.format(err),_logger.LogLevel.ERROR)

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
                _logger.log('[' + __name__ + '] ts3 error: "{0}"'.format(err),_logger.LogLevel.ERROR)


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
