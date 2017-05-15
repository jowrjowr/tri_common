def discord_forward(message, dest='ping_forwarding'):

    import common.logger as _logger
    import common.credentials.discord as _discord
    import discord
    import asyncio

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    client = discord.Client(loop=loop,cache_auth=False)

    @client.event
    async def on_ready():
        _logger.log('[' + __name__ + '] Discord connected', _logger.LogLevel.DEBUG)

        # channel ids are integer but have to be quoted?
        channel = _discord.Channel[dest].value
        channel = client.get_channel('{}'.format(channel))
        result = await client.send_message(channel, message)
        _logger.log('[' + __name__ + '] message sent, disconnecting', _logger.LogLevel.DEBUG)

        return await client.logout()
    try:
        _logger.log('[' + __name__ + '] Discord message to channel {0}: "{1}"'.format(dest, message), _logger.LogLevel.DEBUG)
        client.run(_discord.token)
        _logger.log('[' + __name__ + '] disconnected. job done.', _logger.LogLevel.DEBUG)
    except Exception as error:
        _logger.log('[' + __name__ + '][sovereign] Discord connection error: ' + str(error), _logger.LogLevel.ERROR)

