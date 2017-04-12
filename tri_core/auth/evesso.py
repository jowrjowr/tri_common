#!/usr/bin/python3


def auth_evesso():
    from flask import request, url_for, Response, session, redirect, make_response
    from requests_oauthlib import OAuth2Session

    import common.logger as _logger

    client_id = _eve.client_id
    client_secret = _eve.client_secret
    redirect_url = _eve.redirect
    client_id = '586228c3770847b0a865cf89ae6f0c90'
    client_secret = '7MuEgxidtoIQBiU8jp9fv6qplYqa0h02RwidI4Yo'
    redirect_url = 'https://auth.triumvirate.rocks/eve/callback'

    base_url = 'https://login.eveonline.com'
    token_url = base_url + '/oauth/token'
    base_auth_url = base_url + '/oauth/authorize'

    # setup the redirect url for the first stage of oauth flow
    scope = ['publicData', 'characterAccountRead', 'characterCalendarRead']
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

    import common.logger as _logger
    import common.credentials.eve as _eve
    import common.database as _database
    import tri_core.common.session as _session
    import json
    import requests
    import datetime
    import uuid
    import time

    import MySQLdb as mysql
    import common.request_esi

    client_id = _eve.client_id
    client_secret = _eve.client_secret
    redirect_url = _eve.redirect
    client_id = '586228c3770847b0a865cf89ae6f0c90'
    client_secret = '7MuEgxidtoIQBiU8jp9fv6qplYqa0h02RwidI4Yo'
    redirect_url = 'https://auth.triumvirate.rocks/eve/callback'

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

    # validate that the person who wants services is, in fact, blue to us

    try:
        request_url = 'https://api.triumvirate.rocks/core/isblue?id={0}'.format(charid)
        result = common.request_esi.esi(__name__, request_url)
    except common.request_esi.NotHttp200 as error:
        _logger.log('[' + __name__ + '] /core/isblue endpoint error ' + str(error.code) + ': ' + str(error.message), _logger.LogLevel.ERROR)
        return('SORRY, INTERNAL API ERROR')
    isblue = json.loads(result)
    isblue = isblue['code']

    if isblue == 0:
        _logger.log('[' + __name__ + '] charid {0} ({1}) is not blue, but wants to be!'.format(charid,charname),_logger.LogLevel.WARNING)
        return('SORRY, YOU HAVE TO BE VANGUARD TO GET VANGUARD SERVICES!')
    elif isblue == 1:
        _logger.log('[' + __name__ + '] charid {0} ({1}) is blue'.format(charid,charname),_logger.LogLevel.INFO)
    else:
        _logger.log('[' + __name__ + '] isblue api error on charid {0} ({1})'.format(charid,charname),_logger.LogLevel.ERROR)
        return('SORRY, INTERNAL API ERROR')

    # register the user in the user database

    # get character affiliations
    # doing via requests directly so no caching the request

    headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}
    request_url = 'https://esi.tech.ccp.is/latest/characters/affiliation/?datasource=tranquility'
    data = '[{}]'.format(charid)
    result = requests.post(request_url, headers=headers, data=data)

    try:
        result.raise_for_status()
    except requests.exceptions.HTTPError as error:
        _logger.log('[' + __name__ + '] unable to get character affiliations for {0}: {1}'.format(charid, error),_logger.LogLevel.ERROR)
        return('ESI ERROR: '.format(error))

    result = json.loads(result.text)
    corpid = result[0]['corporation_id']
    allianceid = result[0]['alliance_id']

    # get corp name
    request_url = esi_url + "/corporations/" + str(corpid) + '/?datasource=tranquility'
    try:
        result = common.request_esi.esi(__name__, request_url)
    except common.request_esi.NotHttp200 as error:
        _logger.log('[' + __name__ + '] /corporations endpoint error ' + str(error.code) + ': ' + str(error.message), _logger.LogLevel.ERROR)
        return('SORRY, INTERNAL API ERROR')

    result = json.loads(result)
    corpname = result['corporation_name']


    # get alliance name
    request_url = esi_url + "/alliances/" + str(allianceid) + '/?datasource=tranquility'
    try:
        result = common.request_esi.esi(__name__, request_url)
    except common.request_esi.NotHttp200 as error:
        _logger.log('[' + __name__ + '] /alliances endpoint error ' + str(error.code) + ': ' + str(error.message), _logger.LogLevel.ERROR)
        return('SORRY, INTERNAL API ERROR')
    result = json.loads(result)
    alliancename = result['alliance_name']

    # setup the service (jabber, mumble, etc) user/pass

    serviceuser = charname
    serviceuser = serviceuser.replace(" ", '')
    serviceuser = serviceuser.replace("'", '')
    servicepass = uuid.uuid4().hex[:8]

    # now dump it all into mysql

    # store our new shiny access token in the user token database

    try:
        sql_conn = mysql.connect(
            database=_database.DB_DATABASE,
            user=_database.DB_USERNAME,
            password=_database.DB_PASSWORD,
            host=_database.DB_HOST)
    except mysql.Error as err:
        _logger.log('[' + __name__ + '] mysql error: ' + str(err), _logger.LogLevel.ERROR)
        return

    cursor = sql_conn.cursor()
    query =  'REPLACE INTO CrestTokens (charID, isValid, accessToken, refreshToken, validUntil, charName, corpID, corpName, allianceID, allianceName) '
    query += 'VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)'

    try:
        row = cursor.execute(
            query, (
                charid,
                1,
                access_token,
                refresh_token,
                expires_at,
                charname,
                corpid,
                corpname,
                allianceid,
                alliancename,
            ),
        )
    except Exception as errmsg:
        _logger.log('[' + __name__ + '] mysql error: ' + str(errmsg), _logger.LogLevel.ERROR)
        return('MySQL error :(')

    # store user data in users table
    query =  'REPLACE INTO Users (charID, charName, corpID, corpName, allianceID, allianceName, ServiceUsername, ServicePassword, isMain, isAlt)'
    query += 'VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)'

    try:
        row = cursor.execute(
            query, (
                charid,
                charname,
                corpid,
                corpname,
                allianceid,
                alliancename,
                serviceuser,
                servicepass,
                1,
                0,
            ),
        )
    except Exception as errmsg:
        _logger.log('[' + __name__ + '] mysql error: ' + str(errmsg), _logger.LogLevel.ERROR)
        return('MySQL error :(')

    # construct the session and declare victory
    try:
        cookie = _session.makesession(charid, access_token)
        _logger.log('[' + __name__ + '] new user: {0} (charid {1})'.format(charname, charid),_logger.LogLevel.INFO)
    except Exception as error:
        _logger.log('[' + __name__ + '] unable to construct session for charid {0}: {1}'.format(charid, error),_logger.LogLevel.ERROR)
        return 'ERROR: Unable to construct session cookie :('
    finally:
        cursor.close()
        sql_conn.commit()
        sql_conn.close()

    # setup services

    #### JABBER

    # construct the login cookie

    expire_date = datetime.datetime.now()
    expire_date = expire_date + datetime.timedelta(days=7)

    response = make_response(redirect('https://www.triumvirate.rocks'))
    response.set_cookie('tri_core', cookie, domain='.triumvirate.rocks', expires=expire_date)
    response.set_cookie('tri_charid', str(charid), domain='.triumvirate.rocks', expires=expire_date)
    return response
