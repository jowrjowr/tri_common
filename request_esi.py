def do_esi(function, url, method, charid=None, data=None, version='latest', base='esi', extraheaders={}):

    import requests
    import common.logger as _logger
    import common.ldaphelpers as _ldaphelpers
    import logging
    import json
    import redis
    from cachecontrol import CacheControl
    from cachecontrol.caches.redis_cache import RedisCache
    from common.graphite import sendmetric
    from common.credentials.g_translate import translate_api_key
    from commands.maint.tokens import eve_tokenthings

    # headers

    useragent = 'triumvirate services - yell at saeka'
    headers = {'Accept': 'application/json', 'User-Agent': useragent, 'Accept-Encoding': 'gzip'}

    if method == 'post':
        # add a header for POST data
        headers['Content-Type'] = 'application/json'

    if extraheaders is not {}:
        # add any custom headers as necessary
        headers.update(extraheaders)

    # shut the FUCK up.
    logging.getLogger("requests").setLevel(logging.WARNING)

    # if a charid is specified, this is going to be treated as an authenticated request
    # where an access token is added to the esi request url automatically

    # snag the user's tokens from ldap
    if charid is not None:

        _logger.log('[' + __name__ + '] authenticated {0} request for {1}: {2}'.format(base, charid, url),_logger.LogLevel.DEBUG)

        dn = 'ou=People,dc=triumvirate,dc=rocks'
        filterstr='(uid={})'.format(charid)
        attrlist=[ 'esiAccessToken', 'esiAccessTokenExpires', 'discordAccessToken', ]
        code, result = _ldaphelpers.ldap_search(__name__, dn, filterstr, attrlist)

        if code == False:
            _logger.log('[' + __name__ + '] LDAP connectionerror: {}'.format(error),_logger.LogLevel.ERROR)
            js = { 'error': 'internal ldap error'}
            return 500, js

        if result == None:
            js = { 'error': 'no tokens for uid {0}'.format(charid)}
            return 500, js

        (dn, result), = result.items()

        esi_atoken = result.get('esiAccessToken')
        esi_atoken_expires = result.get('esiAccessTokenExpires')
        discord_atoken = result.get('discordAccessToken')

        if esi_atoken == None and base == 'esi':
            js = { 'error': 'no stored esi access token'}
            return 400, js

        if discord_atoken == None and base == 'discord':
            js = { 'error': 'no stored discord access token'}
            return 400, js

        # make sure the ESI token is current if this is an ESI request

        if base == 'esi' or base == 'esi_verify':
            # at this point it this is an authenticated request.
            # make sure that the token retrieved is current. if it is not, update it.

            pass

    else:
        _logger.log('[' + __name__ + '] unauthenticated {0} request: {1}'.format(base, url),_logger.LogLevel.DEBUG)
        token_header = dict()

    # construct the full request url including api version

    # request_esi hits more than just ESI-specific stuff, so some scoping of the base is necessary

    if base == 'esi':
        # ESI ofc
        base_url = 'https://esi.tech.ccp.is/' + version

        if charid is not None:
            # add the authenticated header
            headers['Authorization'] = 'Bearer {0}'.format(esi_atoken)
    elif base == 'discord':
        # discord api
        base_url = 'https://discordapp.com/api/' + version

        if charid is not None:
            # add the authenticated header
            headers['Authorization'] = 'Bearer {0}'.format(discord_atoken)

    elif base == 'zkill':
        # zkillboard
        base_url = 'https://zkillboard.com/api'
    elif base == 'esi_verify':
        # special case where the endpoint isn't versioned
        base_url = 'https://esi.tech.ccp.is'
        if charid is not None:
            # add the authenticated header
            headers['Authorization'] = 'Bearer {0}'.format(esi_atoken)
    elif base == 'triapi':
        # tri api
        base_url = 'https://api.triumvirate.rocks'
    elif base == 'oauth':
        # eve oauth
        base_url = 'https://login.eveonline.com/oauth'
    elif base == 'g_translate':
        # google translate
        base_url = 'https://translation.googleapis.com/language/translate/v2'
        base_url += '?key={0}&target=en&source=text&model=nmt&'.format(translate_api_key)
    elif base == 'eve_market':
        # eve marketdata
        base_url = 'https://api.eve-marketdata.com/api/'

    # special google translate bullshit

    if base == 'g_translate':
        full_url = base_url + url
    else:
        full_url = base_url + '/' + url

    # setup redis caching for the requests object
    r = redis.StrictRedis(host='localhost', port=6379, db=0)
    session = requests.Session()
    # redis does not actually connect above, i have to specifically test

    try:
        r.client_list()
        session = CacheControl(session, RedisCache(r))
    except redis.exceptions.ConnectionError as err:
        sendmetric(function, base, 'request', 'rediserror', 1)
        _logger.log('[' + function + '] Redis connection error: ' + str(err), _logger.LogLevel.ERROR)
    except redis.exceptions.ConnectionRefusedError as err:
        sendmetric(function, base, 'request', 'rediserror', 1)
        _logger.log('[' + function + '] Redis connection error: ' + str(err), _logger.LogLevel.ERROR)
    except Exception as err:
        sendmetric(function, base, 'request', 'rediserror', 1)
        logger.error('[' + function + '] Redis generic error: ' + str(err))

    # do the request, but catch exceptions for connection issues

    timeout = 10
    try:
        if method == 'post':
            request = session.post(full_url, headers=headers, timeout=timeout, data=data)
        elif method == 'get':
            request = session.get(full_url, headers=headers, timeout=timeout)

    except requests.exceptions.ConnectionError as err:
        sendmetric(function, base, 'request', 'connection_error', 1)
        _logger.log('[' + function + '] ESI connection error:: ' + str(err), _logger.LogLevel.WARNING)
        return(500, { 'error': 'API connection error: ' + str(err)})
    except requests.exceptions.ReadTimeout as err:
        sendmetric(function, base, 'request', 'read_timeout', 1)
        _logger.log('[' + function + '] ESI connection read timeout: ' + str(err), _logger.LogLevel.WARNING)
        return(500, { 'error': 'API connection read timeout: ' + str(err)})
    except requests.exceptions.Timeout as err:
        sendmetric(function, base, 'request','timeout' , 1)
        _logger.log('[' + function + '] ESI connection timeout: ' + str(err), _logger.LogLevel.WARNING)
        return(500, { 'error': 'API connection timeout: ' + str(err)})
    except requests.exceptions.SSLError as err:
        sendmetric(function, base, 'request','ssl_error' , 1)
        _logger.log('[' + function + '] ESI SSL error: ' + str(err), _logger.LogLevel.WARNING)
        return(500, { 'error': 'API connection timeout: ' + str(err)})
    except Exception as err:
        sendmetric(function, base, 'request', 'general_error', 1)
        _logger.log('[' + function + '] ESI generic error: ' + str(err), _logger.LogLevel.WARNING)
        return(500, { 'error': 'General error: ' + str(err)})

    # need to also check that the api thinks this was success.

    if not request.status_code == 200:
        sendmetric(function, base, 'request', 'failure', 1)
        # don't bother to log 404 and 403s
        if not request.status_code == 404 and not request.status_code == 403:
            _logger.log('[' + function + '] ESI API error ' + str(request.status_code) + ': ' + str(request.text), _logger.LogLevel.WARNING)
            _logger.log('[' + function + '] ESI API error URL: ' + str(url), _logger.LogLevel.WARNING)
    else:
        sendmetric(function, base, 'request', 'success', 1)

    # check for warning headers. mostly for esi.

    warning = request.headers.get('warning')
    pages = request.headers.get('X-Pages')

    if pages:
        msg = '{0} total pages'.format(pages)
        _logger.log('[' + function + '] {0}'.format(msg), _logger.LogLevel.DEBUG)

    if warning:
        msg = '{0} deprecated endpoint: {1} - {2}'.format(base, url, warning)
        _logger.log('[' + function + '] {0}'.format(msg), _logger.LogLevel.WARNING)

    # do metrics

    elapsed_time = request.elapsed.total_seconds()
    sendmetric(function, base, 'request', 'elapsed', elapsed_time)
    sendmetric(function, base, 'request', request.status_code, 1)

    # shouldn't have to typecast it but sometimes:
    # TypeError: the JSON object must be str, not 'LocalProxy'
    try:
        result = json.loads(str(request.text))
    except TypeError as error:
        msg = 'google CDN error - cant convert esi response to json'
        _logger.log('[' + function + '] {0}'.format(msg), _logger.LogLevel.WARNING)
        return(500, { 'code': 500, 'error': msg })

    return(request.status_code, result)


def esi(function, url, method='get', charid=None, data=None, version='latest', base='esi', extraheaders=dict()):
    from common.graphite import sendmetric
    import common.logger as _logger
    import time

    # wrap around do_esi so we can do retries!

    retry_max = 5
    retry_count = 0
    sleep = 1

    while (retry_count < retry_max):
        if retry_count > 0:
            _logger.log('[' + function + '] ESI retry {0} of {1}'.format(retry_count, retry_max), _logger.LogLevel.WARNING)
        code, result = do_esi(function, url, method, charid, data, version, base, extraheaders)
        # the only thing that's worth retrying are on 5xx errors, everything else is game

        if code >= 500:
            retry_count += 1
            sendmetric(function, base, 'request', 'retry' , 1)
            _logger.log('[' + function + '] ESI call failed. sleeping {0} seconds before retrying'.format(sleep), _logger.LogLevel.WARNING)
            time.sleep(1)
        else:
            return(code, result)
    sendmetric(function, base, 'request', 'retry_maxed', 1)
    _logger.log('[' + function + '] ESI call failed {0} times. giving up. '.format(retry_max), _logger.LogLevel.WARNING)
    # return the last code/result
    return(code, result)
