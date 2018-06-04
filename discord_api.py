def discord_forward(message, server=269991543627055114, dest='ping_forwarding'):

    import common.logger as _logger
    import common.credentials.discord as _discord
    import discord
    import asyncio

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    client = discord.Client(loop=loop,cache_auth=False)

    token = None

    if server == 358117641724100609:
        token = _discord.social_token
    elif server == 269991543627055114:
        token = _discord.leadership_token
    else:
        return False

    @client.event
    async def on_ready():
        _logger.log('[' + __name__ + '] Discord connected', _logger.LogLevel.DEBUG)

        client.change_presence(game=None, status='invisible', afk=False)

        # channel ids are integer but have to be quoted?
        channel = _discord.Channel[dest].value
        channel = client.get_channel('{}'.format(channel))
        result = await client.send_message(channel, message)
        _logger.log('[' + __name__ + '] message sent, disconnecting', _logger.LogLevel.DEBUG)

        return await client.logout()
    try:
        _logger.log('[' + __name__ + '] Discord message to channel {0}: "{1}"'.format(dest, message), _logger.LogLevel.DEBUG)
        client.run(token)
        _logger.log('[' + __name__ + '] disconnected. job done.', _logger.LogLevel.DEBUG)
    except Exception as error:
        _logger.log('[' + __name__ + '][sovereign] Discord connection error: ' + str(error), _logger.LogLevel.ERROR)


def discord_members(function, target_channel):

    import common.logger as _logger
    import common.credentials.discord as _discord
    import discord
    import asyncio

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    client = discord.Client(loop=loop,cache_auth=False)

    users = [ None ]
    @client.event
    async def on_ready():
        _logger.log('[' + function + '] Discord connected', _logger.LogLevel.DEBUG)
        servers = client.servers
        members = [ None ]
        channel = _discord.Channel[target_channel].value
        channel = client.get_channel('{}'.format(channel))
        for server in servers:
            client.request_offline_members(server)
            if server.name == 'Vanguard Leadership Discord':
                members = server.members

        for member in members:
            if member.bot == True:
                #print('bot: {}'.format(member.name))
                pass
            # only look at people who can read text in the channel
            perms = channel.permissions_for(member)
            if perms.read_messages == True:
                if member.nick == None:
                    users.append(member.name)
                else:
                    users.append(member.nick)

        await client.close()
    try:
        client.run(_discord.token)
        return users
        _logger.log('[' + function + '] discord disconnected. job done.', _logger.LogLevel.DEBUG)
    except Exception as error:
        _logger.log('[' + function + '] discord connection error: ' + str(error), _logger.LogLevel.ERROR)

def discord_allmembers(function, login_type, token=None, user=None, exclude=[], include=[]):

    import common.logger as _logger
    import discord
    import asyncio
    import time
    import logging

    logging.getLogger('discord.state').setLevel(logging.CRITICAL)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    client = discord.Client(loop=loop,cache_auth=False)

    users = dict()
    @client.event
    async def on_ready():
        _logger.log('[' + function + '] Discord connected', _logger.LogLevel.DEBUG)
        client.change_presence(game=None, status='invisible', afk=False)
        servers = client.servers
        for server in servers:

            users[server.id] = []

            large = server.large
            if large == True:
                # as per discord api, "large" servers won't return offline members
                client.request_offline_members(server)

            if server.name in exclude:
                msg = 'excluding discord: {0}'.format(server.name)
                _logger.log('[' + function + '] {0}'.format(msg), _logger.LogLevel.DEBUG)
                # do not fetch members from this named discord
                continue

            if server.name in include or include == []:
                msg = 'including discord: {0}'.format(server.name)
                _logger.log('[' + function + '] {0}'.format(msg), _logger.LogLevel.DEBUG)
                # only fetch specifically included discords
                pass
            else:
                msg = 'excluding discord: {0}'.format(server.name)
                _logger.log('[' + function + '] {0}'.format(msg), _logger.LogLevel.DEBUG)
                continue

            members = server.members

            for member in members:
                member_detail = dict()

                # map the join time to epoch
                joined_at = member.joined_at
                joined_at = time.mktime(joined_at.timetuple())
                joined_at = int(joined_at)

                member_detail['id'] =  member.id
                member_detail['bot'] =  member.bot
                member_detail['name'] = member.name
                member_detail['display_name'] = member.display_name
                member_detail['server_name'] = member.server.name
                member_detail['server_id'] = member.server.id
                member_detail['discriminator'] = member.discriminator
                member_detail['joined_at'] = joined_at
                member_detail['status'] = str(member.status)
                member_detail['member_nick'] = member.nick
                member_detail['top_role'] = str(member.top_role)
                member_detail['server_permissions'] = member.server_permissions.value

                users[server.id].append(member_detail)

        await client.close()
    try:
        if login_type == 'token':
            client.run(token)
        if login_type == 'user':
            username, password = user
            client.run(username, password)
        return users

        _logger.log('[' + function + '] discord disconnected. job done.', _logger.LogLevel.DEBUG)
    except Exception as error:
        _logger.log('[' + function + '] discord connection error: ' + str(error), _logger.LogLevel.ERROR)

def discord_userdetails(function, login_type, token=None, user=None, target_server=None, target_member=None):

    import common.logger as _logger
    import discord
    import asyncio
    import logging

    logging.getLogger('discord.state').setLevel(logging.CRITICAL)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    client = discord.Client(loop=loop,cache_auth=False)

    details = dict()

    @client.event
    async def on_ready():
        _logger.log('[' + function + '] Discord connected', _logger.LogLevel.DEBUG)
        client.change_presence(game=None, status='invisible', afk=False)

        for server in client.servers:
            if server.name == target_server:
                # we're only looking at a specific server

                members = server.members

                for member in members:

                    if member.name == target_member:
                        # specific server, specific member.
                        details['joined_at'] = member.joined_at
                        details['status'] = member.status
                        details['id'] = member.id
                        details['created_at'] = member.created_at
                        details['bot'] = member.bot

                        # some assembly required

                        details['roles'] = []
                        details['permissions'] = []
                        for role in member.roles:
                            details['roles'].append(role.name)

                        details['top_role'] = member.top_role.name

                        for perm in iter(member.server_permissions):
                            details['permissions'].append(perm)

        await client.close()
    try:
        if login_type == 'token':
            client.run(token)
        if login_type == 'user':
            username, password = user
            client.run(username, password)
        return details

        _logger.log('[' + function + '] discord disconnected. job done.', _logger.LogLevel.DEBUG)
    except Exception as error:
        _logger.log('[' + function + '] discord connection error: ' + str(error), _logger.LogLevel.ERROR)

