def do_forums(function, endpoint, method, *data):

    import requests
    import common.logger as _logger
    from common.graphite import sendmetric
    import common.credentials.forums as _forums
    import logging
    import json
    import redis
    from cachecontrol import CacheControl
    from cachecontrol.caches.redis_cache import RedisCache

    # reference:
    # https://invisionpower.com/developers/rest-api

    # shut the FUCK up.
    logging.getLogger("requests").setLevel(logging.WARNING)

    # setup redis caching for the requests object
    r = redis.StrictRedis(host='localhost', port=6379, db=0)
    session = requests.Session()
    # redis does not actually connect above, i have to specifically test

    try:
        r.client_list()
        session = CacheControl(session, RedisCache(r))
    except redis.exceptions.ConnectionError as err:
        sendmetric(function, 'forums', 'api_request', 'rediserror', 1)
        _logger.log('[' + function + '] Redis connection error: ' + str(err), _logger.LogLevel.ERROR)
    except redis.exceptions.ConnectionRefusedError as err:
        sendmetric(function, 'forums', 'api_request', 'rediserror', 1)
        _logger.log('[' + function + '] Redis connection error: ' + str(err), _logger.LogLevel.ERROR)
    except Exception as err:
        sendmetric(function, 'forums', 'api_request', 'rediserror', 1)
        logger.error('[' + function + '] Redis generic error: ' + str(err))

    # do the request, but catch exceptions for connection issues

    url = _forums.base_url + endpoint
    timeout = 5

    try:
        if method == 'post':
            data = data[0]
            headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}
            request = session.post(url, headers=headers, timeout=timeout, data=data, auth=(_forums.api_key, '' ))
        elif method == 'get':
            headers = {'Accept': 'application/json'}
            request = session.get(url, headers=headers, timeout=timeout, auth=(_forums.api_key, '' ))

    except requests.exceptions.ConnectionError as err:
        sendmetric(function, 'forums', 'api_request', 'connection_error', 1)
        _logger.log('[' + function + '] forum api connection error:: ' + str(err), _logger.LogLevel.ERROR)
        return(500, { 'code': 500, 'error': 'API connection error: ' + str(err)})
    except requests.exceptions.ReadTimeout as err:
        sendmetric(function, 'forums', 'api_request', 'read_timeout', 1)
        _logger.log('[' + function + '] forum api connection read timeout: ' + str(err), _logger.LogLevel.ERROR)
        return(500, { 'code': 500, 'error': 'API connection read timeout: ' + str(err)})
    except requests.exceptions.Timeout as err:
        sendmetric(function, 'forums', 'api_request','timeout' , 1)
        _logger.log('[' + function + '] forum api connection timeout: ' + str(err), _logger.LogLevel.ERROR)
        return(500, { 'code': 500, 'error': 'forum API connection timeout: ' + str(err)})
    except Exception as err:
        sendmetric(function, 'forums', 'api_request', 'general_error', 1)
        _logger.log('[' + function + '] forum api generic error: ' + str(err), _logger.LogLevel.ERROR)
        return(500, { 'code': 500, 'error': 'General error: ' + str(err)})

    # need to also check that the api thinks this was success.

    if not request.status_code == 200:
        sendmetric(function, 'forums', 'api_request', 'failure', 1)
        # don't bother to log 404s
        if not request.status_code == 404:
            _logger.log('[' + function + '] forum API error ' + str(request.status_code) + ': ' + str(request.text), _logger.LogLevel.ERROR)
            _logger.log('[' + function + '] forum API error URL: ' + str(url), _logger.LogLevel.ERROR)
    else:
        sendmetric(function, 'forums', 'api_request', 'success', 1)

    # do metrics

    elapsed_time = request.elapsed.total_seconds()
    sendmetric(function, 'forums', 'api_request', 'elapsed', elapsed_time)
    sendmetric(function, 'forums', 'api_request', request.status_code, 1)

    return(request.status_code, request.text)


def forums(function, endpoint, method='get', *data):

    from common.graphite import sendmetric
    import common.logger as _logger
    import time

    # optional arg gets wrapped in a tuple?
    if len(data) > 0:
        data = data[0]

    # wrap around do_forums so we can do retries!

    retry_max = 5
    retry_count = 0
    sleep = 1

    while (retry_count < retry_max):
        if retry_count > 0:
            _logger.log('[' + function + '] forum api retry {0} of {1}'.format(retry_count, retry_max), _logger.LogLevel.WARNING)
        code, result = do_forums(function, endpoint, method, data)

        # the only thing that's worth retrying are on 5xx errors, everything else is game

        if code >= 500:
            retry_count += 1
            sendmetric(function, 'forums', 'api_request', 'retry' , 1)
            _logger.log('[' + function + '] forum api call failed. sleeping {0} seconds before retrying'.format(sleep), _logger.LogLevel.WARNING)
            time.sleep(1)
        else:
            return(code, result)
    sendmetric(function, 'forums', 'api_request', 'retry_maxed', 1)
    _logger.log('[' + function + '] forum call failed {0} times. giving up. '.format(retry_max), _logger.LogLevel.ERROR)
    # return the last code/result
    return(code, result)
