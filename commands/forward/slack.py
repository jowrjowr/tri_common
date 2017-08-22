from slackclient import SlackClient
from time import sleep
import requests
import re
import common.logger as _logger
import time
def start_slack(username, password, covername, handler, server, discord_queue):

    # build the login session for slack

    s = requests.Session()

    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:55.0) Gecko/20100101 Firefox/55.0'}

    url = 'https://' + server + '/'
    r = s.get(url, headers=headers)
    code = r.status_code

    if not code == 200:
        msg = 'unable to connect to {0} slack. http code {0}'.format(covername, code)
        _logger.log('[' + __name__ + '] {0}'.format(msg), _logger.LogLevel.ERROR)
        msg = '```diff' + '\n' + '- {0} offline```'.format(covername)
        discord_queue.put(msg)
        return

    # need to fetch a hidden form value associated with the session cookie
    # it is of the form: <input type="hidden" name="crumb" value="s-1503129907-027251bef8-☃" />

    crumb = None

    lines = r.text.split('\n')
    regex = r'.*<input type="hidden" name="crumb" value="(\S+)" />.*'
    for line in lines:
        match = re.match(regex, line)
        if match:
            crumb = match.group(1)
            continue

    if crumb is None:
        msg = 'cannot find {0} slack form crumb'.format(covername)
        _logger.log('[' + __name__ + '] {0}'.format(msg), _logger.LogLevel.ERROR)
        msg = '```diff' + '\n' + '- {0} offline```'.format(covername)
        discord_queue.put(msg)
        return

    # try to login

    form = dict()
    form['signin'] = 1
    form['redir'] = ''
    form['crumb'] = crumb
    form['email'] = username
    form['password'] = password
    form['remember'] = ''

    r = s.post(url, headers=headers, data=form)

    code = r.status_code

    if not code == 200:
        msg = 'unable to login to {0} slack. http code {1}'.format(covername, code)
        _logger.log('[' + __name__ + '] {0}'.format(msg), _logger.LogLevel.ERROR)
        msg = '```diff' + '\n' + '- {0} offline```'.format(covername)
        discord_queue.put(msg)
        return

    # a http 200 doesn't _necessarily_ mean we are logged in

    token = None

    lines = r.text.split('\n')
    regex = r".*api_token: '(\S+)'.*"
    for line in lines:
        match = re.match(regex, line)
        if match:
            token = match.group(1)
            continue

    if token is None:
        msg = 'unable to locate slack token. wrong pw?'
        _logger.log('[' + __name__ + '] {0}'.format(msg), _logger.LogLevel.ERROR)
        msg = '```diff' + '\n' + '- {0} offline```'.format(covername)
        discord_queue.put(msg)
        return
    client = SlackClient(token)

    if not client.rtm_connect():
        msg = 'unable to connect to {0} slack api'.format(covername)
        _logger.log('[' + __name__ + '] {0}'.format(msg), _logger.LogLevel.ERROR)
        msg = '```diff' + '\n' + '- {0} offline```'.format(covername)
        discord_queue.put(msg)
        return

    tick = 0
    while True:
        process_update( discord_queue, covername, client, client.rtm_read() )
        tick += 1
        if tick % 3600 == 0:
            # every hour log that you are alive
            msg = '{1} life ping'.format(covername)
            _logger.log('[' + __name__ + '] {0}'.format(msg), _logger.LogLevel.INFO)

        sleep(1)

    msg = '{0} slack irrevocably disconnected'.format(covername)
    _logger.log('[' + __name__ + '] {0}'.format(msg), _logger.LogLevel.ERROR)
    msg = '```diff' + '\n' + '- {0} offline```'.format(covername)
    discord_queue.put(msg)

def process_update(discord_queue, covername, client, item):

    # each item seems to be a hash within an array
    # api documented here:
    # https://api.slack.com/rtm#events

    if len(item) == 0:
        return
    else:
        item = item[0]

    msg = '{0} slack debug. item: {1}'.format(covername, item)
    _logger.log('[' + __name__ + '] {0}'.format(msg), _logger.LogLevel.INFO)
    # past here, each update has a distinct type which we are interested in

    item_type = item['type']

    if item_type == 'hello':
        # the connection was just established. announce an online state.

        msg = '{0} slack online'.format(covername)
        _logger.log('[' + __name__ + '] {0}'.format(msg), _logger.LogLevel.INFO)
        msg = '```diff' + '\n' + '+ {0} online```'.format(covername)
        discord_queue.put(msg)

    if item_type == 'message':
        # this a message of some sort.
        process_message(discord_queue, covername, client, item)

def process_message(discord_queue, covername, client, item):

    print(item)

    timestamp = int(float(item['ts']))
    channel_id = item['channel']
    sender_id = item['user']
    content = item['text']

    # get my info

    user = client.api_call("auth.test")
    user_id = user['user_id']
    user_name = user['user']

    # map the ids to names

    sender = client.api_call("users.info", user=sender_id)
    sender_name = sender['user']['name']

    # channels can be of 3 types:
    # 1: public channel. this is covered by a channels.info call
    # 2: locked channel: same, but groups.info
    # 3: private message: neither

    priv_channel = client.api_call("groups.info", channel=channel_id)
    pub_channel = client.api_call("channels.info", channel=channel_id)

    if priv_channel.get('error') and pub_channel.get('error') == 'channel_not_found':
        # this is a private message, forward this.
        msg = '{0} direct message from {1}: {2}'.format(covername, sender_name, content)
        _logger.log('[' + __name__ + '] {0}'.format(msg), _logger.LogLevel.INFO)

        ping = '--------------------\n'
        ping += 'DM FROM: {0}\n'.format(sender_name)
        ping += 'MESSAGE: {0}\n\n'.format(content)
        ping = "**[{0}]** | __{1}__\n```css\n{2}```".format(covername, time.strftime("%H:%M:%S %z / %d-%m-%Y", time.localtime(timestamp)), ping)

        # send to discord
        discord_queue.put(ping)
        return

    # past here, this will be a direct channel message which won't always be forwarded

    elif priv_channel.get('error') is not None and pub_channel.get('error') is None:
        # public channel
        channel_name = '#' + pub_channel['channel']['name']
    elif priv_channel.get('error') is None and pub_channel.get('error') is not None:
        # private channel
        channel_name = u"\U0001F512" + priv_channel['group']['name']
    else:
        # something fucking broke but we'll try anyway
        channel_name = None

    # we only want to forward broadcast messages, so there needs to be filters

    matches = []

    matches.append(r'(.*)<!here\|@here>(.*)')       # active ppl in channel
    matches.append(r'(.*)<!channel>(.*)')           # all ppl in channel
    matches.append(r'(.*)<!everyone>(.*)')            # all ppl everywhere
    matches.append(r'(.*)<@{}>(.*)'.format(user_id))    # just me

    matchcount = 0
    for regex in matches:
        match = re.match(regex, content)
        if match:
            content = match.group(1) + '@_some_crap' + match.group(2)
            matchcount = 1
            continue

    if matchcount == 0:
        # this item won't be forwarded. yawn.
        return

    # we have a message to forward

    msg = '{0} ping message from {1} in channel {2}: {3}'.format(covername, sender_name, channel_name, content)
    _logger.log('[' + __name__ + '] {0}'.format(msg), _logger.LogLevel.INFO)

    ping = '--------------------\n'
    ping += 'CHANNEL: {0} || FROM: {1}\n'.format(channel_name, sender_name)
    ping += 'MESSAGE: {0}\n\n'.format(content)
    ping = "**[{0}]** | __{1}__\n```css\n{2}```".format(covername, time.strftime("%H:%M:%S %z / %d-%m-%Y", time.localtime(timestamp)), ping)

    # send to discord
    discord_queue.put(ping)
