from telethon import TelegramClient
from telethon.tl.types import UpdatesTg
from telethon.tl.types.update_new_message import UpdateNewMessage
import common.logger as _logger
from googleapiclient.discovery import build
import time
from common.discord_api import discord_forward

def new_thing(object):

    # look for pings from the xdeath bot


    # looking for specific kinds of update objects that indicate a direct message

    if not isinstance(object, UpdatesTg): return

    updates = object.updates
    users = object.users
    date = object.date

    # one update can contain multiple messages and users

    for user, item in zip(users, updates):

        # we only care about actual messages, not minor things.
        if not isinstance(item, UpdateNewMessage): continue

        username = user.username

        # we only care about message from the bot

        if not username == 'xxdeathxx_bot': continue

        content = item.message.message
        en_content = rus_to_en(content)

        cover = 'xdeathx'

        ping = '--------------------\n'
        ping += 'ORIGINAL RUS: {0}\n\n'.format(content)
        ping += 'ENGLISH: {0}\n'.format(en_content)
        ping = "**[{0}]** | __{1}__\n```css\n{2}```".format(cover, time.strftime("%H:%M:%S %z / %d-%m-%Y", time.localtime(None)), ping)
        discord_forward(ping)

def forward_telegram_xdeath():

    # constants

    session_id = 'xdeath'
    api_id = 162703
    api_hash = 'a622b5bb39628b28c8aea61da7ef8bf9'
    phone = '+79859500067'

    # test

#    api_id = 176423
#    api_hash = '0c726ce6fdd2045ed32335604241b4dd'
#    phone = '+4255223596'

    # construct client

    client = TelegramClient(session_id, api_id, api_hash)
    client.connect()

    # this will create a session file in CWD named "session_id".session
    if not client.is_user_authorized():
        print('reeee')
        client.send_code_request(phone)
        client.sign_in(phone, input('Enter code: '))

    # pickup the last so many dialogs (distinct groups/messages?) sent to the client

    dialogs, entities = client.get_dialogs(10)

    # this is currently the xdeath bot, but the ordering might change? we'll see.
    # seems to follow the client ordering, starting frm top down with index 0
    entity = entities[1]
    #entity = entities[2]

    total_count, messages, senders = client.get_message_history(entity, limit=10)

    for msg, sender in zip(reversed(messages), reversed(senders)):

        try:
            username = sender.username
            content = msg.message
            date = msg.date
        except Exception as e:
            continue
        # we don't care about non-ping messages

        if not username == 'xxdeathxx_bot': continue

        en_content = rus_to_en(content)

        print('ping:')
        print('date: {0}'.format(date))
        print('original: {0}'.format(content))
        print('english: {0}'.format(en_content))
        print('')

    # infinite loop to monitor for updates
    client.add_update_handler(new_thing)
    while True:
        time.sleep(1)
#        print('waking up!')
    return


def rus_to_en(content):

    # translate content to english

    translate_api = 'AIzaSyBnWXRMQjbsJafFLpMcgFKqXYR-40yj_Jw'

    service = build('translate', 'v2', developerKey=translate_api)

    result = service.translations().list(
        source='ru',
        target='en',
        q=content
    ).execute()

    result = result.get('translations')
    result = result[0]
    result = result.get('translatedText')

    return result

forward_telegram_xdeath()
