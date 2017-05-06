#!/usr/bin/python3

import time
import discord
import asyncio
import re as _re

import common.credentials.discord as _discord
import common.logger as _logger

def start_discord(username, password, covername, handler, discord_queue):

    prefix = '[' + __name__ + '][' + username + '] '

    _logger.log(prefix + 'starting up', _logger.LogLevel.INFO)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    client = discord.Client(loop=loop,cache_auth=False)

    @client.event
    async def on_ready():
        _logger.log(prefix + 'connected to discord', _logger.LogLevel.DEBUG)

    @client.event
    async def on_message(message):

        #now = time.localtime(None)
        #now_friendly = time.strftime("%Y-%m-%d @ %H:%M:%S %z", now)
        #header = '[' + str(covername) + ']'
        #header = header + '\t' + 'Time: {0}, covername: {1}'.format(str(now_friendly), covername)
        #header = header + '\n'
        #header = header + '----------' + '\n'

        if message.mention_everyone:
            #body = 'FROM: {0}, DISCORD SERVER: {1}, CHANNEL: #{2} \n'.format(str(message.author),str(message.server), str(message.channel))
            #body = body + str(message.content).replace('@','#') + '\n'
            #discord_queue.put(header + body)

            discord_queue.put(parse_message(str(covername), message))

    try:
        client.run(username, password)
    except Exception as error:
        _logger.log(prefix + 'Discord connection error: ' + str(error), _logger.LogLevel.ERROR)

def parse_message(cover, message):
    if cover == "low effort horde spy":
        body = horde_parser(message)
    elif cover == "GOTG":
        body = gotg_parser(message)
    else:
        body = default_parser(message)

    return "**[{0}]** | __{1}__\n```css\n{2}```"\
        .format(cover, time.strftime("%H:%M:%S %z / %d-%m-%Y", time.localtime(None)), body)

def default_parser(message):
    return "FROM: {0} | {1}\nCHANNEL: {2}\n--------------------\n{3}"\
        .format(str(message.author),str(message.server), str(message.channel), str(message.content).replace('@','#'))

def gotg_parser(message):
    try:
        text = message.content.splitlines()

        ping_from = text[1].split(" ", 1)[-1]
        ping_to = text[2].split(" ", 1)[-1]

        return "FROM: {0} | {1}\nTO: {2} (CHANNEL:{3})\n--------------------\n{4}" \
            .format(ping_from, str(message.server), ping_to, str(message.channel),
                    str("\n".join(text[3:])).replace('@', '#'))
    except Exception:
        return default_parser(message)

def horde_parser(message):
    try:
        text = message.content

        author_clean = str(message.author)[:-5]

        mentions = [mention for mention in text.split() if mention.startswith('@')]

        textwords = [word for word in text if word not in mentions]

        return "FROM:  | {1}\nTO: {2} (CHANNEL:{3})\n--------------------\n{4}" \
            .format(author_clean, str(message.server), ", ".join(mentions).replace('@', ''), str(message.channel),
                    str(text).replace('@', '#'))
    except Exception:
        return default_parser(message)