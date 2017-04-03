#!/usr/bin/python3

import sleekxmpp
import sys
import netifaces
import xmltodict
import dns.resolver
import common.logger as _logger
from common.discord_api import discord_forward
from IPy import IP

class Jabber(sleekxmpp.ClientXMPP):

    # an abstract identifier for opsec purposes

    identifier = 'unknown'
    sessionid = 'unknown'

    def __init__(self, identifier, jid, password, sessionid):
        super(Jabber, self).__init__(jid, password)
        self.identifier = identifier
        self.sessionid = sessionid
        # ping
        self.register_plugin('xep_0199')
        # service discovery
        self.register_plugin('xep_0030')
        ## add xmpp event handlers

        # does something:

        self.add_event_handler('session_start', self.start)
        self.add_event_handler('failed_auth', self.failure)

    def failure(self, event):
        _logger.log('[' + str(self.identifier) + '] Unable to login user',_logger.LogLevel.ERROR)
        self.disconnect(reconnect=False, wait=False, send_close=True)

    def start(self, event):
        #self.send_presence(ptype='away', ppriority='-1')

        # this is the meat of this tool.
        # an unconfigured python client will have a default client type as "bot"
        # we do not want this.

        # https://xmpp.org/extensions/xep-0030.html#schemas-info
        try:
            print(self.sessionid)
            items_xml = self['xep_0030'].get_info(
                jid         =   self.sessionid,
                local       =   False,
                block       =   True,
            )
        except sleekxmpp.exceptions.IqTimeout as error:
            # maybe setup a retry loop? idk
            _logger.log('[' + __name__ + '] Disconnecting due to timeout on get_info query to {0}'.format(self.sessionid),_logger.LogLevel.WARNING)
            return
        except sleekxmpp.exceptions.IqError as error_xml:
            error = xmltodict.parse(str(error_xml))
            _logger.log('[' + __name__ + '] Client {0} does not support disco_info queries'.format(self.sessionid),_logger.LogLevel.WARNING)
            return
        finally:
            # once we get the disco_info response we are done no matter what
            self.disconnect(reconnect=False, wait=False, send_close=True)
        print(items_xml)

        items = xmltodict.parse(str(items_xml))
        try:
            identity = items['iq']['query']['identity']
            id_cat = identity['@category']
            id_type = identity['@type']
            if id_type == 'bot':
                _logger.log('[' + __name__ + '] BOT type detected on jid: {0} (category: {1})'.format(self.sessionid,id_cat),_logger.LogLevel.WARNING)

        except sleekxmpp.exceptions.IqError as error:
            _logger.log('[' + __name__ + '] error queryin jid {0}: {1}'.format(self.sessionid, error),_logger.LogLevel.ERROR)

        except KeyError as error:
            # this only happens on goofball identity responses or blowback from timeouts
            pass


def audit_bothunt():

    import common.credentials.jabber as _jabber
    import common.logger as _logger
    import common.credentials.bothunt as _bothunt

    import logging
    import requests
    import json

    _logger.log('[' + __name__ + '] auditing jabber active sessions',_logger.LogLevel.DEBUG)

    logging.getLogger("requests").setLevel(logging.WARNING)

    # get all jabber users
    headers = {'Accept': 'application/json', 'Content-Type': 'application/json', 'Authorization': str(_jabber.atoken)}

    # hardcode service user for testing
    jabber_url = _jabber.baseurl + 'sessions/'

    try:
        request = requests.get(jabber_url, headers=headers, timeout=10)
    except Exception as err:
        pass

    if request.status_code == 404:
        _logger.log('[' + __name__ + '] jabber /users endpoint does not exist?!',_logger.LogLevel.WARNING)

    if request.status_code != 200 and request.status_code != 404:
        # errors that aren't "not found":
        # hard fail on breakage? not sure.
        _logger.log('[' + __name__ + '] Unable to access /users endpoint',_logger.LogLevel.WARNING)
        return

    result_parsed = json.loads(request.text)

    for session in result_parsed['session']:

        sessionid = session['sessionId']
        sessionid_base = sessionid.split('/')[0]
        ip = session['hostAddress']
        user = _bothunt.user
        password = _bothunt.password
        server = _bothunt.server
        jid = user.lower() + '@' + server

        # do not check my own session
        if not jid == sessionid_base:

            # test client ip for a tor exit node
            test_tor(ip, sessionid)

            # test jabber client directly for lazy bots
            _logger.log('[' + __name__ + '] checking session: {0} from: {1}'.format(sessionid, ip),_logger.LogLevel.INFO)
            jabber = Jabber('bothunt',jid, password, sessionid)
            jabber.connect()
            jabber.process(block=False)

    return

def test_tor(ip, sessionid):

    # test if the jabber ip is coming from a tor exit node
    # see: http://www.torproject.org/projects/tordnsel.html.en
    _logger.log('[' + __name__ + '] Testing for tor presence on jid {0} @ {1}'.format(sessionid, ip),_logger.LogLevel.DEBUG)
    clientip_reverse = reverse_ip(ip)
    hostip = netifaces.ifaddresses('enp2s0')[2][0]['addr']
    hostip_reverse = reverse_ip(hostip)
    query = clientip_reverse + '.' + '5222' + '.' + hostip_reverse + '.ip-port.exitlist.torproject.org'
    try:
        answers = dns.resolver.query(query, 'A')
        # there should NEVER be a response for non-tor clients.
        _logger.log('[' + __name__ + '] TOR detected on jid: {0} @ {1}'.format(sessionid, ip),_logger.LogLevel.WARNING)
    except dns.resolver.NXDOMAIN:
        # user passed
        pass
    return

def reverse_ip(ip):
    if len(ip) <= 1:
       return ip
    l = ip.split('.')
    return '.'.join(l[::-1])
