# handles all the bubblewrap associated with an ESI request
# keeps the recycling to a minimum

def esi(function, url):

    import requests
    import requests_cache
    import common.logger as _logger
    import logging
    import json
    import redis

    # without configuring logging, requests will spew connection nonsense to log
    logging.getLogger("requests").setLevel(logging.WARNING)

    headers = {'Accept': 'application/json'}

    # setup redis caching for the requests object
    # half hour cache seems like a reasonable start

    # not quitting on redis errors as they aren't fatal
    r = redis.StrictRedis(host='localhost', port=6379, db=0)

    # redis does not actually connect above, i have to specifically test

    try:
        r.client_list()
        requests_cache.install_cache(cache_name='esi_cache', backend='redis', expire_after=1800, connection=r)
    except redis.exceptions.ConnectionError as err:
        print(err)
        _logger.log('[' + function + '] Redis connection error: ' + str(err), _logger.LogLevel.ERROR)
    except redis.exceptions.ConnectionRefusedError as err:
        print(err)
        _logger.log('[' + function + '] Redis connection error: ' + str(err), _logger.LogLevel.ERROR)
    except Exception as err:
        print(err)
        logger.error('[' + function + '] Redis generic error: ' + str(err))

    # do the request, but catch exceptions for connection issues
    try:
        request = requests.get(url, headers=headers, timeout=10)
    except requests.exceptions.ConnectionError as err:
        _logger.log('[' + function + '] ESI connection error:: ' + str(err), _logger.LogLevel.ERROR)
        js = json.dumps({ 'code': 500, 'error': 'API connection error: ' + str(err)})
        return js
    except requests.exceptions.ReadTimeout as err:
        _logger.log('[' + function + '] ESI connection error: ' + str(err), _logger.LogLevel.ERROR)
        js = json.dumps({ 'code': 500, 'error': 'API connection timeout: ' + str(err)})
        return js
    except requests.exceptions.Timeout as err:
        _logger.log('[' + function + '] ESI connection error: ' + str(err), _logger.LogLevel.ERROR)
        js = json.dumps({ 'code': 500, 'error': 'API connection timeout: ' + str(err)})
        return js
    except Exception as err:
        _logger.log('[' + function + '] ESI connection error: ' + str(err), _logger.LogLevel.ERROR)
        js = json.dumps({ 'code': 500, 'error': 'General error: ' + str(err)})
        return js

    # need to also check that the api thinks this was success.

    if not request.status_code == 200:
        # don't bother to log 404s
        if not request.status_code == 404:
            _logger.log('[' + function + '] ESI API error ' + str(request.status_code) + ': ' + str(request.text), _logger.LogLevel.ERROR)
            _logger.log('[' + function + '] ESI API error URL: ' + str(url), _logger.LogLevel.ERROR)
        raise NotHttp200(request.status_code, request.text)

    # assume everything is ok. return json result.

    return request.text


class Error(Exception):
    pass

class NotHttp200(Error):
    def __init__(self, code, message):
        self.code = code
        self.message = message
