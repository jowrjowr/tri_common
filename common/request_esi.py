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

    # snag the user's ldap token
    if charid is not None:
        _logger.log('[' + __name__ + '] authenticated esi request for {0}: {1}'.format(charid, url),_logger.LogLevel.DEBUG)

        dn = 'ou=People,dc=triumvirate,dc=rocks'
        code, result = _ldaphelpers.ldap_search(__name__, dn, '(uid={})'.format(charid), ['esiAccessToken'])

        if code == 'error':
            _logger.log('[' + __name__ + '] LDAP connectionerror: {}'.format(error),_logger.LogLevel.ERROR)
            js = { 'error': 'internal ldap error'}
            return 500, js

        if result == None:
            js = { 'error': 'no token for uid {0}'.format(charid)}
            return 500, js

        (dn, result), = result.items()

        atoken = result.get('esiAccessToken')

        if atoken == None:
            js = { 'error': 'no access token'}
            return 400, js

    else:
        _logger.log('[' + __name__ + '] unauthenticated esi request: {0}'.format(url),_logger.LogLevel.DEBUG)
        token_header = dict()

    # construct the full request url including api version

    # request_esi hits more than just ESI-specific stuff, so some scoping of the base is necessary

    if base == 'esi':
        # ESI ofc
        base_url = 'https://esi.tech.ccp.is'+ '/' + version

        if charid is not None:
            # add the authenticated header
            headers['Authorization'] = 'Bearer {0}'.format(atoken)

    elif base == 'zkill':
        # zkillboard
        base_url = 'https://zkillboard.com/api'
    elif base == 'esi_verify':
        # special case where the endpoint isn't versioned
        base_url = 'https://esi.tech.ccp.is'
    elif base == 'triapi':
        # tri api
        base_url = 'https://api.triumvirate.rocks'
    elif base == 'oauth':
        # eve oauth
        base_url = 'https://login.eveonline.com/oauth'

    url = base_url + '/' + url

    # setup redis caching for the requests object
    r = redis.StrictRedis(host='localhost', port=6379, db=0)
    session = requests.Session()
    # redis does not actually connect above, i have to specifically test

    try:
        r.client_list()
        session = CacheControl(session, RedisCache(r))
    except redis.exceptions.ConnectionError as err:
        sendmetric(function, 'esi', 'request', 'rediserror', 1)
        _logger.log('[' + function + '] Redis connection error: ' + str(err), _logger.LogLevel.ERROR)
    except redis.exceptions.ConnectionRefusedError as err:
        sendmetric(function, 'esi', 'request', 'rediserror', 1)
        _logger.log('[' + function + '] Redis connection error: ' + str(err), _logger.LogLevel.ERROR)
    except Exception as err:
        sendmetric(function, 'esi', 'request', 'rediserror', 1)
        logger.error('[' + function + '] Redis generic error: ' + str(err))

    # do the request, but catch exceptions for connection issues

    timeout = 10
    try:
        if method == 'post':
            request = session.post(url, headers=headers, timeout=timeout, data=data)
        elif method == 'get':
            request = session.get(url, headers=headers, timeout=timeout)

    except requests.exceptions.ConnectionError as err:
        sendmetric(function, 'esi', 'request', 'connection_error', 1)
        _logger.log('[' + function + '] ESI connection error:: ' + str(err), _logger.LogLevel.WARNING)
        return(500, { 'error': 'API connection error: ' + str(err)})
    except requests.exceptions.ReadTimeout as err:
        sendmetric(function, 'esi', 'request', 'read_timeout', 1)
        _logger.log('[' + function + '] ESI connection read timeout: ' + str(err), _logger.LogLevel.WARNING)
        return(500, { 'error': 'API connection read timeout: ' + str(err)})
    except requests.exceptions.Timeout as err:
        sendmetric(function, 'esi', 'request','timeout' , 1)
        _logger.log('[' + function + '] ESI connection timeout: ' + str(err), _logger.LogLevel.WARNING)
        return(500, { 'error': 'API connection timeout: ' + str(err)})
    except Exception as err:
        sendmetric(function, 'esi', 'request', 'general_error', 1)
        _logger.log('[' + function + '] ESI generic error: ' + str(err), _logger.LogLevel.WARNING)
        return(500, { 'error': 'General error: ' + str(err)})

    # need to also check that the api thinks this was success.

    if not request.status_code == 200:
        sendmetric(function, 'esi', 'request', 'failure', 1)
        # don't bother to log 404 and 403s
        if not request.status_code == 404 and not request.status_code == 403:
            _logger.log('[' + function + '] ESI API error ' + str(request.status_code) + ': ' + str(request.text), _logger.LogLevel.WARNING)
            _logger.log('[' + function + '] ESI API error URL: ' + str(url), _logger.LogLevel.WARNING)
    else:
        sendmetric(function, 'esi', 'request', 'success', 1)

    # do metrics

    elapsed_time = request.elapsed.total_seconds()
    sendmetric(function, 'esi', 'request', 'elapsed', elapsed_time)
    sendmetric(function, 'esi', 'request', request.status_code, 1)

    # shouldn't have to typecast it but sometimes:
    # TypeError: the JSON object must be str, not 'LocalProxy'
    try:
        result = json.loads(str(request.text))
    except TypeError as error:
        return(500, { 'code': 500, 'error': 'cant convert esi response to json'})

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
            sendmetric(function, 'esi', 'request', 'retry' , 1)
            _logger.log('[' + function + '] ESI call failed. sleeping {0} seconds before retrying'.format(sleep), _logger.LogLevel.WARNING)
            time.sleep(1)
        else:
            return(code, result)
    sendmetric(function, 'esi', 'request', 'retry_maxed', 1)
    _logger.log('[' + function + '] ESI call failed {0} times. giving up. '.format(retry_max), _logger.LogLevel.WARNING)
    # return the last code/result
    return(code, result)
