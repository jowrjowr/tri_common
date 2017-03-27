#!/usr/bin/python3

import sleekxmpp
import xmltodict
import time
import common.logger as _logger
import common.database as _database
import MySQLdb as mysql
import discord
import argparse

from queue import Queue
from sleekxmpp import ClientXMPP
from sleekxmpp.exceptions import IqError, IqTimeout
from common.discord_api import discord_forward
import common.credentials.discord as _discord

from concurrent.futures import ThreadPoolExecutor

import forward.discord
import forward.jabber

if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('--debug', help="full debug output", action="store_true")
    args = parser.parse_args()

    # initialize logging
    if args.debug:
        log_lvl = _logger.LogLevel.DEBUG
    else:
        log_lvl = _logger.LogLevel.INFO

    log_mod = _logger.LogMode.DAILY
    log_fmt = _logger.LogFormat.TIMESTAMP
    _logger.init(log_lvl=log_lvl, log_mod=log_mod, log_fmt=log_fmt)

    _logger.log('[' + __name__ + '] spy forwarder starting up', _logger.LogLevel.INFO)

    # get our list of spies
    try:
        sql_conn = mysql.connect(
            database=_database.DB_DATABASE,
            user=_database.DB_USERNAME,
            password=_database.DB_PASSWORD,
            host=_database.DB_HOST)
    except mysql.Error as err:
        _logger.log('[' + __name__ + '] mysql error: ' + str(err), _logger.LogLevel.ERROR)
        sys.exit(1)

    cursor = sql_conn.cursor()
    query = 'SELECT id, covername, username, password, server, handler, server_type FROM Spies'
    try:
        count = cursor.execute(query)
        rows = cursor.fetchall()
    except Exception as err:
        _logger.log('[' + __name__ + '] mysql error: ' + str(err), _logger.LogLevel.ERROR)
        sys.exit(1)
    finally:
        cursor.close()
        sql_conn.close()

    _logger.log('[' + __name__ + '] registered spies: {0}'.format(count), _logger.LogLevel.INFO)

    # shoot each discord instance into a thread that will operate
    # asynchronously, while sending messages into a queue that also operates
    # in an async fashion.

    pool = ThreadPoolExecutor(count + 1)
    discord_queue = Queue()

    for row in rows:
        covername = row[1]
        username = row[2]
        password = row[3]
        server = row[4]
        handler = row[5]
        server_type = row[6]

        if server_type == 'discord':
            pool.submit(forward.discord.start_discord, username, password, covername, handler, discord_queue)
        if server_type == 'jabber':
            jid = username + '@' + server
            pool.submit(forward.jabber.start_jabber, jid, password, covername, handler, discord_queue)

    while True:
        _logger.log('[' + __name__ + '] waiting for queue messages', _logger.LogLevel.DEBUG)
        item = discord_queue.get()
        item = str(item) + '\n' + '----------'
        pool.submit(discord_forward, item)
        discord_queue.task_done()
        time.sleep(1)

