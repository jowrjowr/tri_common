# handles all the bubblewrap associated with an ESI request
# keeps the recycling to a minimum

def request_esi(url):

    import requests
    import json

    headers = {'Accept': 'application/json'}

    # do the request, but catch exceptions for connection issues
    try:
        request = requests.get(url, headers=headers)
    except ConnectionError as err:
        js = json.dumps({ 'code': 500, 'error': 'API connection error: ' + str(err)})
        return re
    except Timeout as err:
        js = json.dumps({ 'code': 500, 'error': 'API connection timeout: ' + str(err)})
        return re

    ##### TODO: ACTUAL LOGGING OF ISSUES SUCH AS THIS

    # need to also check that the api thinks this was success.

    if not 200 <= request.status_code <=299:
        js = json.dumps({ 'code': request.status_code, 'error': 'API error on url: ' + str(url) + ' http code: ' + str(request.status_code) })
        return js

    # assume everything is ok. return json result.

    return request.text
