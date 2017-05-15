def auth_evesso():
    from flask import request, url_for, Response, session, redirect, make_response, request
    from requests_oauthlib import OAuth2Session

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
    _logger.securitylog(__name__, 'SSO login initiated', ipaddress=ipaddress)

    # setup the redirect url for the first stage of oauth flow
    scope = ['publicData', 'characterAccountRead']
    scope += ['characterChatChannelsRead', 'characterClonesRead', 'characterContactsRead']
    scope += ['characterLocationRead', 'characterNotificationsRead', 'characterSkillsRead']
    scope += ['characterStatsRead', 'corporationAssetsRead', 'corporationContactsRead']
    scope += ['corporationContractsRead', 'corporationMembersRead', 'corporationStructuresRead']
    scope += ['esi-clones.read_clones.v1', 'esi-characters.read_contacts.v1']
    scope += ['esi-corporations.read_corporation_membership.v1', 'esi-location.read_location.v1']
    scope += ['esi-location.read_ship_type.v1', 'esi-skills.read_skillqueue.v1', 'esi-skills.read_skills.v1']
    scope += ['esi-universe.read_structures.v1', 'esi-corporations.read_structures.v1', 'esi-search.search_structures.v1']

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
    auth_url, state = oauth_session.authorization_url(base_auth_url)
    session['oauth_state'] = state
    return redirect(auth_url, code=302)



def auth_evesso_callback():

    from flask import request, url_for, Response, session, redirect, make_response
    from requests_oauthlib import OAuth2Session
    
    from tri_core.common.register import registeruser
    from tri_core.common.storetokens import storetokens

    import common.logger as _logger
    import common.credentials.eve as _eve
    import tri_core.common.session as _session
    import tri_core.common.testing as _testing
    import json
    import requests
    import datetime
    import uuid
    import time

    import common.request_esi

    client_id = _eve.client_id
    client_secret = _eve.client_secret
    redirect_url = _eve.redirect_url

    esi_url = 'https://esi.tech.ccp.is/latest'
    base_url = 'https://login.eveonline.com'
    token_url = base_url + '/oauth/token'
    verify_url = base_url + '/oauth/verify'

    # the user has (ostensibly) authenticated with the application, now
    # the access token can be fetched

    _logger.log('[' + __name__ + '] eve SSO callback received',_logger.LogLevel.INFO)

    oauth_session = OAuth2Session(
        client_id=client_id,
        state=session.get('oauth2_state'),
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
    _logger.securitylog(__name__, 'SSO callback completed', charid=charid, ipaddress=ipaddress)

    if status == False:
        if details == 'error':
            _logger.log('[' + __name__ + '] error in testing user {0}'.format(charid),_logger.LogLevel.ERROR)
            message = 'SORRY. There was an issue registering. Try again.'
        if details == 'banned':
            _logger.log('[' + __name__ + '] banned user {0} ({1}) tried to register'.format(charid, charname),_logger.LogLevel.WARNING)
            _logger.securitylog(__name__, 'banned user tried to register', charid=charid, ipaddress=ipaddress)
            message = 'nope.avi'
        if details == 'public':
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
        cookie = _session.makesession(charid, access_token)
        _logger.log('[' + __name__ + '] created session for user: {0} (charid {1})'.format(charname, charid),_logger.LogLevel.INFO)
    except Exception as error:
        _logger.log('[' + __name__ + '] unable to construct session for charid {0}: {1}'.format(charid, error),_logger.LogLevel.ERROR)
        return 'ERROR: Unable to construct session cookie :('

    if details == 'registered':
        # user is blue and already in the system. just refresh the api tokens.
        _logger.log('[' + __name__ + '] user {0} ({1}) already registered'.format(charid, charname),_logger.LogLevel.INFO)
        _logger.securitylog(__name__, 'core login', charid=charid, ipaddress=ipaddress)
        storetokens(charid, access_token, refresh_token)
    else:
        _logger.log('[' + __name__ + '] user {0} ({1}) not registered'.format(charid, charname),_logger.LogLevel.INFO)
        # user is blue but unregistered
        _logger.securitylog(__name__, 'core user registered', charid=charid, ipaddress=ipaddress)
        registeruser(charid, access_token, refresh_token)
        # maybe setup services here?

    expire_date = datetime.datetime.now()
    expire_date = expire_date + datetime.timedelta(days=7)

    response = make_response(redirect('https://www.triumvirate.rocks'))
    response.set_cookie('tri_core', cookie, domain='.triumvirate.rocks', expires=expire_date)
    response.set_cookie('tri_charid', str(charid), domain='.triumvirate.rocks', expires=expire_date)
    return response

