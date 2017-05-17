def do_esi(function, url, method, charid=None, data=None):

    import requests
    import common.logger as _logger
    import common.credentials.ldap as _ldap
    import logging
    import json
    import redis
    import ldap
    from cachecontrol import CacheControl
    from cachecontrol.caches.redis_cache import RedisCache
    from common.api import base_url
    from common.graphite import sendmetric

    # shut the FUCK up.
    logging.getLogger("requests").setLevel(logging.WARNING)

    # if a charid is specified, this is going to be treated as an authenticated request
    # where an access token is added to the esi request url automatically

    # snag the user's ldap token
    if not charid == None:
        _logger.log('[' + __name__ + '] authenticated esi request for {0}: {1}'.format(charid, url),_logger.LogLevel.DEBUG)
        # setup ldap
        ldap_conn = ldap.initialize(_ldap.ldap_host, bytes_mode=False)
        try:
            ldap_conn.simple_bind_s(_ldap.admin_dn, _ldap.admin_dn_password)
        except ldap.LDAPError as error:
            _logger.log('[' + __name__ + '] LDAP connection error: {}'.format(error),_logger.LogLevel.ERROR)
            js = { 'error': 'internal ldap error'}
            return 500, js
        # snag the token
        try:
            result = ldap_conn.search_s('ou=People,dc=triumvirate,dc=rocks', ldap.SCOPE_SUBTREE, filterstr='(&(objectclass=pilot)(uid={0}))'.format(charid), attrlist=['esiAccessToken'])
            user_count = result.__len__()
        except ldap.LDAPError as error:
            _logger.log('[' + __name__ + '] unable to fetch ldap information: {}'.format(error),_logger.LogLevel.ERROR)
            js = { 'error': 'internal ldap error'}
            return 500, js
        # this shouldn't happen often tbh
        if user_count == 0:
            js = { 'error': 'no token for uid {0}'.format(charid)}
            return 500, js

        dn, atoken = result[0]
        try:
            atoken = atoken['esiAccessToken'][0].decode('utf-8')
            url = url + '&token=' + atoken
        except KeyError as error:
            js = { 'error': 'no access token'}
            return 400, js
    else:
        _logger.log('[' + __name__ + '] unauthenticated esi request: {0}'.format(url),_logger.LogLevel.DEBUG)

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

    timeout = 5
    try:

        # test first that eve is online. this will fail if ESI or EVE are down.

        headers = {'Accept': 'application/json'}
        status_url = base_url + 'status/?datasource=tranquility'
        request = requests.get(status_url, headers=headers, timeout=2)
        # we don't really care about the response past 200-or-not
        if not request.status_code == 200:
            _logger.log('[' + function + '] EVE offline / ESI down', _logger.LogLevel.WARNING)
            sendmetric(function, 'esi', 'request', 'offline', 1)
            try:
                result = json.loads(str(request.text))
            except TypeError as error:
                result = { 'error': 'cant convert esi response to json'}
            finally:
                return(500, result)

        # okay probably worked, send the request

        if method == 'post':
            headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}
            request = session.post(url, headers=headers, timeout=timeout, data=data)
        elif method == 'get':
            headers = {'Accept': 'application/json'}
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
        # don't bother to log 404s
        if not request.status_code == 404:
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


def esi(function, url, method='get', charid=None, data=None):
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
        code, result = do_esi(function, url, method, charid, data)
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
