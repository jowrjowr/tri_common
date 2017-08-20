from telethon import TelegramClient
from telethon.tl.types import UpdatesTg
from telethon.tl.types.update_short_message import UpdateShortMessage
import common.logger as _logger
import common.request_esi
import urllib
import time

def new_thing(discord_queue, object):

    # this specifically processes update objects from telegram


    # looking for specific kinds of update objects that indicate a direct message

    if not isinstance(object, UpdateShortMessage): return

    content = object.message
    date = object.date

#    if not username == 'xxdeathxx_bot': continue

    en_content = rus_to_en(content)

    msg = 'xdeath ping (rus): {0}'.format(content)
    _logger.log('[' + __name__ + '] {0}'.format(msg), _logger.LogLevel.INFO)
    msg = 'xdeath ping (eng): {0}'.format(en_content)
    _logger.log('[' + __name__ + '] {0}'.format(msg), _logger.LogLevel.INFO)

    cover = 'xdeathx'

    ping = '--------------------\n'
    ping += 'ORIGINAL RUS: {0}\n\n'.format(content)
    ping += 'ENGLISH: {0}\n'.format(en_content)
    ping = "**[{0}]** | __{1}__\n```css\n{2}```".format(cover, time.strftime("%H:%M:%S %z / %d-%m-%Y", time.localtime(None)), ping)
    discord_queue.put(msg)

def start_telegram(discord_queue):
    # right now just xdeath

    forward_telegram_xdeath(discord_queue)

def forward_telegram_xdeath(discord_queue):

    # constants

    session_id = 'xdeath'
    api_id = 162703
    api_hash = 'a622b5bb39628b28c8aea61da7ef8bf9'
    phone = '+79859500067'

    # construct client

    client = TelegramClient(session_id, api_id, api_hash)

    try:
        client.connect()
    except Exception as e:
        msg = 'unable to connect to xdeath telegram: {0}'.format(e)
        _logger.log('[' + __name__ + '] {0}'.format(msg), _logger.LogLevel.ERROR)

        msg = '```diff' + '\n' + '- xdeath offline```'
        discord_queue.put(msg)

        return

    # this will create a session file in CWD named "session_id".session
    if not client.is_user_authorized():

        msg = '```diff' + '\n' + '- xdeath AUTHENTICATION REQUIRED```'
        discord_queue.put(msg)

        print('need to reauthorize xdeath tool')
        client.send_code_request(phone)
        client.sign_in(phone, input('Enter code: '))
    else:
        msg = '```diff' + '\n' + '+ xdeath online```'
        discord_queue.put(msg)

    # pickup the last so many dialogs (distinct groups/messages?) sent to the client

    dialogs, entities = client.get_dialogs(10)

    # this is currently the xdeath bot, but the ordering might change? we'll see.
    # seems to follow the client ordering, starting frm top down with index 0

    msg = 'printing last few old xdeath pings'
    _logger.log('[' + __name__ + '] {0}'.format(msg), _logger.LogLevel.INFO)

    for entity in entities:
        total_count, messages, senders = client.get_message_history(entity, limit=5)
        for msg, sender in zip(reversed(messages), reversed(senders)):

            try:
                username = sender.username
                content = msg.message
                date = msg.date
            except Exception as e:
                # if it doesn't resolve, it isn't a message anyway
                continue

            # we don't care about non-ping messages

            if not username == 'xxdeathxx_bot': continue

            en_content = rus_to_en(content)

            msg = 'previous death ping (rus): {0}'.format(content)
            _logger.log('[' + __name__ + '] {0}'.format(msg), _logger.LogLevel.INFO)
            msg = 'previous xdeath ping (eng): {0}'.format(en_content)
            _logger.log('[' + __name__ + '] {0}'.format(msg), _logger.LogLevel.INFO)

    # infinite loop to monitor for updates
    client.add_update_handler(discord_queue, new_thing)
    tick = 0
    while True:
        time.sleep(1)
        tick += 1
        if tick % 3600 == 0:
            # every hour log that you are alive
            msg = 'xdeath life ping'
            _logger.log('[' + __name__ + '] {0}'.format(msg), _logger.LogLevel.INFO)
    return


def rus_to_en(content):

    # translate content to english using google translate

    query = dict()
    query['q'] = content
    query['source'] = 'ru'

    query = urllib.parse.urlencode(query)

    code, result = common.request_esi.esi(__name__, query, method='post', base='g_translate')

    if code is not 200:
        msg = 'translation error, http return {0}: {1}'.format(code, result)
        _logger.log('[' + __name__ + '] {0}'.format(msg), _logger.LogLevel.ERROR)
        return None

    try:
        text = result['data']['translations'][0]['translatedText']
    except Exception as e:
        text = None
    finally:
        return text
