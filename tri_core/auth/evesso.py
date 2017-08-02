from flask import request
from tri_api import app

@app.route('/auth/eve/register', methods=['GET'])
def auth_evesso():
    return evesso()

@app.route('/auth/eve/register_alt', methods=['GET'])
def auth_evesso_alt():
    from flask import request
    from tri_core.common.session import readsession
    import common.logger as _logger

    cookie = request.cookies.get('tri_core')

    if cookie == None:
        return make_response('You need to be logged in with your main in order to register an alt')
    else:
        payload = readsession(cookie)
        return evesso(isalt=True, altof=payload['charID'])

def evesso(isalt=False, altof=None):
    from flask import request, Response, session, redirect, make_response
    from requests_oauthlib import OAuth2Session
    from tri_core.common.scopes import scope
    from tri_core.common.session import readsession
    import common.credentials.eve as _eve
    import common.logger as _logger

    client_id = _eve.client_id
    client_secret = _eve.client_secret
    redirect_url = _eve.redirect_url

    base_url = 'https://login.eveonline.com'
    token_url = base_url + '/oauth/token'
    base_auth_url = base_url + '/oauth/authorize'

    # security logging

    ipaddress = request.headers['X-Real-Ip']
    if isalt == True:
        _logger.securitylog(__name__, 'SSO login initiated', ipaddress=ipaddress, detail='alt of {}'.format(altof))
    else:
        _logger.securitylog(__name__, 'SSO login initiated', ipaddress=ipaddress)

    # setup the redirect url for the first stage of oauth flow

    oauth_session = OAuth2Session(
        client_id=client_id,
        scope=scope,
        redirect_uri=redirect_url,
        auto_refresh_kwargs={
            'client_id': client_id,
            'client_secret': client_secret,
        },
        auto_refresh_url=token_url,
    )
    auth_url, state = oauth_session.authorization_url(
        base_auth_url,
        isalt=isalt,
        altof=altof,
        )
    session['oauth2_state'] = state

    # store alt parameters

    session['isalt'] = isalt

    # technically altof will be any previous cookie which can be the same main char. this will be used.
    session['altof'] = altof

    return redirect(auth_url, code=302)

@app.route('/auth/eve/callback', methods=['GET'])
def auth_evesso_callback():

    from flask import request, url_for, Response, session, redirect, make_response
    from requests_oauthlib import OAuth2Session
    from tri_core.common.scopes import scope
    from tri_core.common.register import registeruser
    from tri_core.common.storetokens import storetokens
    from common.check_scope import check_scope

    import common.logger as _logger
    import common.credentials.eve as _eve
    import tri_core.common.session as _session
    import tri_core.common.testing as _testing
    import json
    import requests
    import datetime
    import uuid
    import time

    client_id = _eve.client_id
    client_secret = _eve.client_secret
    redirect_url = _eve.redirect_url

    base_url = 'https://login.eveonline.com'
    token_url = base_url + '/oauth/token'
    verify_url = base_url + '/oauth/verify'

    # the user has (ostensibly) authenticated with the application, now
    # the access token can be fetched

    altof = session.get('altof')
    isalt = session.get('isalt')
    state = session.get('oauth2_state')

    print('alt of: {}'.format(altof))
    print('isalt: {}'.format(isalt))

    if altof == None:
        _logger.log('[' + __name__ + '] SSO callback received',_logger.LogLevel.INFO)
    else:
        _logger.log('[' + __name__ + '] SSO callback received (alt of {0})'.format(altof),_logger.LogLevel.INFO)

    oauth_session = OAuth2Session(
        client_id=client_id,
        state=state,
        redirect_uri=redirect_url,
        auto_refresh_kwargs={
            'client_id': client_id,
            'client_secret': client_secret,
        },
        auto_refresh_url=token_url,
    )

    try:
        atoken = oauth_session.fetch_token(
            token_url,
            client_secret=client_secret,
            authorization_response=request.url,
        )

    except Exception as error:
        _logger.log('[' + __name__ + '] unable to fetch eve sso access token: {0}'.format(error),_logger.LogLevel.ERROR)
        return('ERROR: ' + str(error))

    access_token = atoken['access_token']
    refresh_token = atoken['refresh_token']
    expires_at = atoken['expires_at']

    headers = {'Authorization': 'Bearer ' + access_token }
    result = requests.get(verify_url, headers=headers)

    try:
        result.raise_for_status()
    except requests.exceptions.HTTPError as error:
        _logger.log('[' + __name__ + '] unable to verify eve sso access token: {0}'.format(error),_logger.LogLevel.ERROR)
        return('ERROR: '.format(error))

    tokendata = json.loads(result.text)
    charid = tokendata['CharacterID']
    tokentype = tokendata['TokenType']
    expires_at = tokendata['ExpiresOn']
    charname = tokendata['CharacterName']

    status, details = _testing.usertest(charid)

    # security logging

    ipaddress = request.headers['X-Real-Ip']

    if details == 'isalt' or isalt == True:
        _logger.securitylog(__name__, 'SSO callback completed', charid=charid, ipaddress=ipaddress)
    else:
        _logger.securitylog(__name__, 'SSO callback completed', charid=charid, ipaddress=ipaddress, detail='alt of {0}'.format(altof))

    # store the tokens regardless of their status. we're greedy.
    storetokens(charid, access_token, refresh_token)

    # verify that the atoken we get actually has the correct scopes that we requested
    # just in case someone got cute and peeled some off.

    code, result = check_scope(__name__, charid, scope, atoken=access_token)

    if code == 'error':
        # something in the check broke
        _logger.log('[' + __name__ + '] error in testing scopes for {0}: {1}'.format(charid, result),_logger.LogLevel.ERROR)
        message = 'SORRY, internal error. Try again.'
        response = make_response(message)
        return response

    elif code == False:
        # the user peeled something off the scope list. naughty.
        _logger.log('[' + __name__ + '] user {0} modified scope list. missing: {1}'.format(charid, result),_logger.LogLevel.WARNING)
        _logger.securitylog(__name__, 'core login scope modification', charid=charid, ipaddress=ipaddress)
        message = "Don't tinker with the scope list, please. If you have an issue with it, talk to vanguard leadership."
        response = make_response(message)
        return response
    elif code == True:
        # scopes validate
        _logger.log('[' + __name__ + '] user {0} has expected scopes'.format(charid, result),_logger.LogLevel.DEBUG)

    # for an alt, all we want to do is make the ldap entry and call it a day.

    if isalt == True:
        code, result = registeruser(charid, access_token, refresh_token, isalt, altof)
        if details == 'banned':
            _logger.log('[' + __name__ + '] banned user {0} ({1}) tried to register alt {2}'.format(charid, charname, altof),_logger.LogLevel.WARNING)
            _logger.securitylog(__name__, 'banned user tried to register', charid=charid, ipaddress=ipaddress)
            message = 'nope.avi'
        elif code == True:
            message = 'your alt has been successfully registered.'
            message += '<br>'
            message += 'you can close this window now.'
        else:
            message = 'there was a problem registering your alt. try again.'
        return redirect("https://www.triumvirate.rocks/altregistration")

    # more complex logic for non-alts

    if status == False:
        if details == 'error':
            _logger.log('[' + __name__ + '] error in testing user {0}'.format(charid),_logger.LogLevel.ERROR)
            message = 'SORRY, internal error. Try again.'
        elif details == 'banned':
            _logger.log('[' + __name__ + '] banned user {0} ({1}) tried to register'.format(charid, charname),_logger.LogLevel.WARNING)
            _logger.securitylog(__name__, 'banned user tried to register', charid=charid, ipaddress=ipaddress)
            message = 'nope.avi'
        elif details == 'public':
            _logger.log('[' + __name__ + '] non-blue user {0} ({1}) tried to register'.format(charid, charname),_logger.LogLevel.WARNING)
            _logger.securitylog(__name__, 'non-blue user tried to register', charid=charid, ipaddress=ipaddress)
            message = 'Sorry, you have to be in vanguard to register for vanguard services'
        else:
            # lol should never happen
            _logger.log('[' + __name__ + '] wtf? {0} ({1}) tried to register'.format(charid, charname),_logger.LogLevel.ERROR)
            message = 'SORRY. There was an issue registering. Try again.'

        response = make_response(message)
        return response
    # true status is the only other return value so assume true
    # construct the session and declare victory

    try:
        cookie = _session.makesession(charid, access_token, alt=False)
        _logger.log('[' + __name__ + '] created session for user: {0} (charid {1})'.format(charname, charid),_logger.LogLevel.INFO)
    except Exception as error:
        _logger.log('[' + __name__ + '] unable to construct session for charid {0}: {1}'.format(charid, error),_logger.LogLevel.ERROR)
        return 'ERROR: Unable to construct session cookie :('

    if details == 'registered':
        # user is blue and already in the system. just refresh the api tokens.
        _logger.log('[' + __name__ + '] user {0} ({1}) already registered'.format(charid, charname),_logger.LogLevel.INFO)
        _logger.securitylog(__name__, 'core login', charid=charid, ipaddress=ipaddress)
    else:
        _logger.log('[' + __name__ + '] user {0} ({1}) not registered'.format(charid, charname),_logger.LogLevel.INFO)
        # user is blue but unregistered
        _logger.securitylog(__name__, 'core user registered', charid=charid, ipaddress=ipaddress)
        code, result = registeruser(charid, access_token, refresh_token, isalt=False, altof=None)
        # maybe setup services here?

    expire_date = datetime.datetime.now()
    expire_date = expire_date + datetime.timedelta(days=7)

    response = make_response(redirect('https://www.triumvirate.rocks'))
    response.set_cookie('tri_core', cookie, domain='.triumvirate.rocks', expires=expire_date)
    response.set_cookie('tri_charid', str(charid), domain='.triumvirate.rocks', expires=expire_date)
    return response

