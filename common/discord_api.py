def discord_forward(message):

    import common.logger as _logger
    import common.credentials.discord as _discord
    import discord
    import asyncio

    token = _discord.token
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    client = discord.Client(loop=loop,cache_auth=False)

    @client.event
    async def on_ready():
        _logger.log('[' + __name__ + '] Discord connected', _logger.LogLevel.DEBUG)

        # channel ids are integer but have to be quoted?
        channel = client.get_channel('288786919175749632')
        _logger.log('[' + __name__ + '] Discord message to channel {0}: "{1}"'.format(str(channel),str(message)), _logger.LogLevel.INFO)
        await client.send_message(channel, message)
        await client.close()
    try:
        client.run(token)
    except Exception as error:
        _logger.log('[' + __name__ + '] Discord connection error: ' + str(error), _logger.LogLevel.ERROR)
