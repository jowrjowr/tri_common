#!/usr/bin/python3

import sleekxmpp
import xmltodict
import time
import common.logger as _logger
import common.database as _database
import MySQLdb as mysql
from queue import Queue
from sleekxmpp import ClientXMPP
from sleekxmpp.exceptions import IqError, IqTimeout
from common.discord_api import discord_forward
from concurrent.futures import ThreadPoolExecutor

class JabberForwarder(ClientXMPP):

    def __init__(self, jid, password, covername, handler, queue):
        # connect to jabber
        ClientXMPP.__init__(self, jid, password)
        
        self.queue = queue
        self.identifier = covername
        self.handler = handler
        self.status = 'away'
        self.priority = '100' # -127 to 127 range, higher = more priority over multiple clients

        # xmpp configuration
        self.whitespace_keepalive = True
        self.whitespace_keepalive_interval = 30
        self.auto_reconnect = True
        self.register_plugin('xep_0199') # Ping
        self.register_plugin('xep_0186') # invisibility
        self.register_plugin('xep_0030') # service discovery
        ## add xmpp event handlers

        # https://github.com/fritzy/SleekXMPP/wiki/Event-Index
        self.add_event_handler('session_start', self.start)
        self.add_event_handler('message', self.message)
        self.add_event_handler('failed_auth', self.failure)
        self.add_event_handler('presence', self.presence)

        self['xep_0030'].set_node_handler(
            'get_info',
            jid=None, node=None,  # this will make the handler respond globally, for any JID+node
            handler=self.disco_info
        )
        
    def prefix(self):
        now = time.localtime(None)
        now_friendly = time.strftime("%Y-%m-%d @ %H:%M:%S %z", now)
        prefix = '[' + str(self.identifier) + ']'
        prefix = prefix + '\t' + 'Time: {0}, covername: {1}, owner: {2}'.format(str(now_friendly), self.identifier, self.handler)
        prefix = prefix + '\n'
        prefix = prefix + '----------' + '\n'
        return prefix
        
    def disco_info(self, jid, node, iq):
        # configure bot identity
        # https://github.com/fritzy/SleekXMPP/wiki/XEP-0030:-Working-with-Service-Discovery
        # don't _really_ care, but logging if someone is being nosy to me cant hurt
        disco_details = xmltodict.parse(str(iq))
        noseyprick = disco_details['iq']['@from']
        _logger.log('[' + __name__ + ']' + '[' + str(self.identifier) + '] Discovery info query from {0}'.format(noseyprick),_logger.LogLevel.WARNING)
        info = self['xep_0030'].stanza.DiscoInfo()
        info.add_identity(
            category  = 'client',
            itype     = 'pc',
            name      = None,
        )
        return info

    def failure(self, event):
        _logger.log('[' + __name__ + ']' + '[' + str(self.identifier) + '] Unable to login user',_logger.LogLevel.ERROR)
        self.queue.put(self.prefix() + 'Unable to login user')
    def offline(self, event):
        _logger.log('[' + __name__ + ']' + '[' + str(self.identifier) + '] User offline. Reconnecting',_logger.LogLevel.WARNING)
        self.queue.put(self.prefix() + 'User offline. Reconnecting.')
        self.disconnect(reconnect=True, wait=False, send_close=False)
    def nothing(self, event):
        pass
    def presence(self, event):

        # the only presence we really care about is our own.
        # it's worth knowing spy self-activity

        xml = xmltodict.parse(str(event))
        presence_from = xml['presence']['@from'].split('/')
        whoiam = str(self.boundjid).split('/')

        if presence_from[0] == whoiam[0]:

            try:
                if xml['presence']['status'] == 'Online':
                    _logger.log('[' + __name__ + ']' + '[' + str(self.identifier) + '] Duplicate login',_logger.LogLevel.WARNING)
                    self.queue.put(self.prefix() + 'Duplicate login')
            except KeyError:
                # for some reason not every presence has status?
                pass

    def start(self, event):
        # the bot sits and does nothing once logged in. nothing happens until
        # a message event is received.
        # try to set myself as invisible or at least "not online"
        try:
            self.plugin['xep_0186'].set_invisible()
            _logger.log('[' + __name__ + ']' + '[' + str(self.identifier) + '] User invisible via xep_0186',_logger.LogLevel.INFO)

        except sleekxmpp.exceptions.IqError as error:
            # xep 0186 is not available always. not being there is no big deal.
            # so we'll have to settle for away

            # 'unavailable' works too well with python - you get nothing from the server.
            # the spark client does not do this for some reason?
            pass
        finally:
            self.send_presence(ptype=self.status, ppriority=self.priority)
            _logger.log('[' + str(self.identifier) + '] User online',_logger.LogLevel.INFO)
            self.queue.put(self.prefix() + 'User online')


    def message(self, event):

        # forward the message to discord, including who sent the message

        xml = xmltodict.parse(str(event))
        presence_from = xml['message']['@from'].split('/')
        _logger.log(
            '[' + __name__ + ']' + '[' + str(self.identifier) + '] forwarding message to discord: ', 
            _logger.LogLevel.INFO
        )
        _logger.log(
            '[' + __name__ + ']' + '[' + str(self.identifier) + ']: {0}: {1}'.format(presence_from[0],event['body']), 
            _logger.LogLevel.INFO
        )
        self.queue.put(self.prefix() + '{0}: {1}'.format(presence_from[0],event['body']))

def start_jabber(jid, password, covername, handler, discord_queue):
    _logger.log('[' + __name__ + '] starting spy {0}'.format(jid), _logger.LogLevel.INFO)
    jabber = JabberForwarder(jid, password, covername, handler, discord_queue)

    # this is a polipo http proxy. could possibly use xep_0065 for a socks5 proxy.
    jabber.proxy_config['host'] = '127.0.0.1'
    jabber.proxy_config['port'] = 8123
    jabber.proxy_config['username'] = ''
    jabber.use_proxy = True

    jabber.connect()
    # explicitly nonblocking - care for your threads!
    jabber.process(block=False)

if __name__ == '__main__':

    # initialize logging
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
    query = 'SELECT id, covername, username, password, server, handler FROM Spies'

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


    # shoot each jabber instance into a thread that will operate
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

        jid = username + '@' + server
        pool.submit(start_jabber, jid, password, covername, handler, discord_queue)

    # this infinite loop runs as the "main" thread while jabber instances run in the background
    
    while True:
        _logger.log('[' + __name__ + '] waiting for queue messages', _logger.LogLevel.DEBUG)
        item = discord_queue.get()
        item = str(item) + '\n' + '----------'
        discord_forward(item)
        discord_queue.task_done()
        time.sleep(1)
