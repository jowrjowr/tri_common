# handles all the bubblewrap associated with an ESI request
# keeps the recycling to a minimum

def esi(function, url):

    import requests
    import common.logger as _logger
    import logging
    import json
    import redis
    from cachecontrol import CacheControl
    from cachecontrol.caches.redis_cache import RedisCache

    method = 'get'
    # setup redis caching for the requests object
    r = redis.StrictRedis(host='localhost', port=6379, db=0)
    session = requests.Session()
    # redis does not actually connect above, i have to specifically test

    try:
        r.client_list()
        session = CacheControl(session, RedisCache(r))
    except redis.exceptions.ConnectionError as err:
        _logger.log('[' + function + '] Redis connection error: ' + str(err), _logger.LogLevel.ERROR)
    except redis.exceptions.ConnectionRefusedError as err:
        _logger.log('[' + function + '] Redis connection error: ' + str(err), _logger.LogLevel.ERROR)
    except Exception as err:
        logger.error('[' + function + '] Redis generic error: ' + str(err))

    # do the request, but catch exceptions for connection issues

    headers = {'Accept': 'application/json'}
    timeout=10
    try:

        if method == 'post':
            request = session.post(url, headers=headers, timeout=timeout)
        elif method == 'get':
            request = session.get(url, headers=headers, timeout=timeout)
        else:
            # assume get as a default, also backwards compatibility
            request = session.get(url, headers=headers, timeout=timeout)

    except requests.exceptions.ConnectionError as err:
        _logger.log('[' + function + '] ESI connection error:: ' + str(err), _logger.LogLevel.ERROR)
        return json.dumps({ 'code': 500, 'error': 'API connection error: ' + str(err)})
    except requests.exceptions.ReadTimeout as err:
        _logger.log('[' + function + '] ESI connection read timeout: ' + str(err), _logger.LogLevel.ERROR)
        return json.dumps({ 'code': 500, 'error': 'API connection read timeout: ' + str(err)})
    except requests.exceptions.Timeout as err:
        _logger.log('[' + function + '] ESI connection timeout: ' + str(err), _logger.LogLevel.ERROR)
        return json.dumps({ 'code': 500, 'error': 'API connection timeout: ' + str(err)})
    except Exception as err:
        _logger.log('[' + function + '] ESI generic error: ' + str(err), _logger.LogLevel.ERROR)
        return json.dumps({ 'code': 500, 'error': 'General error: ' + str(err)})

    # need to also check that the api thinks this was success.

    if not request.status_code == 200:
        # don't bother to log 404s
        if not request.status_code == 404:
            _logger.log('[' + function + '] ESI API error ' + str(request.status_code) + ': ' + str(request.text), _logger.LogLevel.ERROR)
            _logger.log('[' + function + '] ESI API error URL: ' + str(url), _logger.LogLevel.ERROR)
        NotHttp200(request.status_code, request.text)

    # assume everything is ok. return json result.

    # shouldn't have to typecast it but sometimes:
    # TypeError: the JSON object must be str, not 'LocalProxy'

    return str(request.text)

class Error(Exception):
    pass

class NotHttp200(Error):
    def __init__(self, code, message):
        self.code = code
        self.message = message
