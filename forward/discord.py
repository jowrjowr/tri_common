#!/usr/bin/python3

import time
import discord
import asyncio

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

        now = time.localtime(None)
        now_friendly = time.strftime("%Y-%m-%d @ %H:%M:%S %z", now)
        header = '[' + str(covername) + ']'
        header = header + '\t' + 'Time: {0}, covername: {1}, owner: {2}'.format(str(now_friendly), covername, handler)
        header = header + '\n'
        header = header + '----------' + '\n'

        if message.mention_everyone:
            body = 'FROM: {0}, DISCORD SERVER: {1}, CHANNEL: #{2} \n'.format(str(message.author),str(message.server), str(message.channel))
            body = body + str(message.content).replace('@','#') + '\n'
            discord_queue.put(prefix + body)

    try:
        client.run(username, password)
    except Exception as error:
        _logger.log(prefix + 'Discord connection error: ' + str(error), _logger.LogLevel.ERROR)
