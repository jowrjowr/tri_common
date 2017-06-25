# broadcast a message to a given jabber group

import sleekxmpp
import common.logger as _logger
import sleekxmpp.plugins.xep_0033 as xep_0033

from sleekxmpp import ClientXMPP, Message
from sleekxmpp.exceptions import IqError, IqTimeout
from sleekxmpp.xmlstream import register_stanza_plugin

class BroadcastBot(ClientXMPP):

    def __init__(self, jid, password, recipients, msg):

        ClientXMPP.__init__(self, jid, password)

        self.recipients = recipients
        self.msg = msg

        # xmpp configuration
        self.ca_certs = None
        self.whitespace_keepalive = False
        self.auto_reconnect = True
        self.response_timeout = 5

        self.register_plugin('xep_0033') # multicast
        self.register_plugin('xep_0030') # service discovery
        # add handlers
        self.add_event_handler('failed_auth', self.failure)
        self.add_event_handler('session_start', self.start)
        self.add_event_handler('ssl_invalid_cert', self.discard)

        # configure pingbomb


    def discard(self, event):
        # https://github.com/fritzy/SleekXMPP/issues/423
        # it is NOT liking the ssl cert...
        return

    def failure(self, event):
        _logger.log('[' + __name__ + '] Unable to login user {0}'.format(self.boundjid),_logger.LogLevel.ERROR)

    def start(self, event):
        _logger.log('[' + __name__ + '] broadcast user online: {0}'.format(self.boundjid),_logger.LogLevel.DEBUG)

        # construct the multi-user msg
        # see: https://github.com/fritzy/SleekXMPP/wiki/Stanzas:-Message
        message = self.Message()
        message['to'] = 'multicast.triumvirate.rocks'
        message['from'] = 'sovereign@triumvirate.rocks'
        message['body'] = self.msg
        message['type'] = 'noreply'
        message['replyto'] = message['from']

        # add the multiple targets. works fine with just one, as well.
        # see: https://xmpp.org/extensions/xep-0033.html
        for jid in self.recipients:
            message['addresses'].addAddress(jid=jid, atype='bcc')

        try:
            result = message.send()
            for address in message['addresses']:
                print(address.get_delivered())
            _logger.log('[' + __name__ + '] User {0} sent broadcast'.format(self.boundjid),_logger.LogLevel.DEBUG)
        except sleekxmpp.exceptions.IqError as error:
            _logger.log('[' + __name__ + '] User {0} unable to send message: {1}'.format(self.boundjid, error),_logger.LogLevel.ERROR)
        finally:
            self.disconnect(wait=True)
            pass

def start_jabber(users, message):

    import common.credentials.broadcast as _broadcast

    user = _broadcast.broadcast_user + '/broadcast'
    password = _broadcast.broadcast_password

    try:
        jabber = BroadcastBot(user, password, users, message)
        jabber.connect(address=('triumvirate.rocks',5222))
        jabber.process(block=False)
        return True
    except Exception as error:
        _logger.log('[' + __name__ + '] User {0} unable to broadcast to users {0}: {1}'.format(user, error),_logger.LogLevel.ERROR)
        return False

def broadcast(message, group):

    # broadcast a message to all the members of a given ldap group

    import ldap
    import common.logger as _logger
    import common.credentials.ldap as _ldap
    from tri_core.common.sashslack import sashslack
    from concurrent.futures import ThreadPoolExecutor
    from collections import defaultdict
    from queue import Queue

    _logger.log('[' + __name__ + '] broadcasting to: {}'.format(group),_logger.LogLevel.INFO)
    _logger.log('[' + __name__ + '] broadcast message: {}'.format(message),_logger.LogLevel.INFO)

    # send message to sash slack
    sashslack(message, group)

    # skip certain users

    skip = [ 'sovereign' ]

    # ldap bind

    ldap_conn = ldap.initialize(_ldap.ldap_host, bytes_mode=False)
    try:
        ldap_conn.simple_bind_s(_ldap.admin_dn, _ldap.admin_dn_password)
    except ldap.LDAPError as error:
        _logger.log('[' + __name__ + '] LDAP connection error: {}'.format(error),_logger.LogLevel.ERROR)
        return False

    # fetch all the users that are in a given jabber group. not using ldap groups, ironically.

    try:
        result = ldap_conn.search_s('ou=People,dc=triumvirate,dc=rocks', ldap.SCOPE_SUBTREE, filterstr='(&(objectclass=pilot)(authGroup={0}))'.format(group), attrlist=['cn'])
        user_count = result.__len__()
    except ldap.LDAPError as error:
        _logger.log('[' + __name__ + '] unable to fetch ldap users: {}'.format(error),_logger.LogLevel.ERROR)
        return False

    _logger.log('[' + __name__ + '] total users in {0}: {1}'.format(group, user_count),_logger.LogLevel.DEBUG)

    users = list()

    for object in result:
        dn, cn = object
        cn = cn['cn'][0]
        cn = cn.decode('utf-8')
        jid = cn + '@triumvirate.rocks'

        if cn not in skip:
            users.append(jid)

    # no attempt is made to break up the users array into smaller chunks.
    # https://docs.ejabberd.im/admin/configuration/#mod-multicast
    # the server will error if the limits aren't set - infinite seems a fair choice.

    start_jabber(users, message)
