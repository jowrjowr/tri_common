# handles all the bubblewrap associated with an ESI request
# keeps the recycling to a minimum

def request_esi(url):

    import requests
    import requests_cache
    import logging
    import json
    import redis

    # without configuring logging, requests will spew connection nonsense to log
    logging.getLogger("requests").setLevel(logging.WARNING)

    headers = {'Accept': 'application/json'}

    # setup redis caching for the requests object
    # half hour cache seems like a reasonable start

    try:
        r = redis.StrictRedis(host='localhost', port=6379, db=0)
        requests_cache.install_cache(cache_name='esi_cache', backend='redis', expire_after=1800, connection=r)
    except ConnectionRefusedError as redis_error:
        logger.error('Unable to connect to redis: ' + str(redis_error))
        pass

    # do the request, but catch exceptions for connection issues
    try:
        request = requests.get(url, headers=headers, timeout=10)
    except ConnectionError as err:
        js = json.dumps({ 'code': 500, 'error': 'API connection error: ' + str(err)})
        return js
    except Timeout as err:
        js = json.dumps({ 'code': 500, 'error': 'API connection timeout: ' + str(err)})
        return js
    except Exception as err:
        js = json.dumps({ 'code': 500, 'error': 'General error: ' + str(err)})
        return js

    ##### TODO: ACTUAL LOGGING OF ISSUES SUCH AS THIS

    # need to also check that the api thinks this was success.

    if not 200 <= request.status_code <=299:
        js = json.dumps({ 'code': request.status_code, 'error': 'API error on url: ' + str(url) + ' http code: ' + str(request.status_code) })
        return js

    # assume everything is ok. return json result.

    return request.text
