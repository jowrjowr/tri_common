#!/usr/bin/python3

from flask import Flask, request, url_for, Response
from flask import g, session, redirect, jsonify, json
from requests_oauthlib import OAuth2Session

import common.logger as _logger
import common.credentials.discord as _discord
import common.database as _database
import MySQLdb as mysql
import flask

def auth_spyregister():

    client_id = _discord.client_id
    client_secret = _discord.client_secret
    redirect = 'https://auth.triumvirate.rocks/5eyes/callback?server_type=discord'
    base_url = 'https://discordapp.com/api'
    base_auth_url = base_url + '/oauth2/authorize'
    token_url = base_url + '/oauth2/token'

    # setup the redirect url for the first stage of oauth flow
    scope = ['identify', 'connections', 'guilds']

    oauth_session = OAuth2Session(
        client_id=client_id,
        scope=scope,
        redirect_uri=redirect,
        auto_refresh_kwargs={
            'client_id': client_id,
            'client_secret': client_secret,
        },
        auto_refresh_url=token_url,
    )
    auth_url, state = oauth_session.authorization_url(base_auth_url)
    session['oauth_state'] = state
    return flask.redirect(auth_url, code=302)

def auth_spyregister_callback():

    client_id = _discord.client_id
    client_secret = _discord.client_secret
    redirect = 'https://auth.triumvirate.rocks/5eyes/callback?server_type=discord'
    base_url = 'https://discordapp.com/api'
    token_url = base_url + '/oauth2/token'
    base_auth_url = base_url + '/oauth2/authorize'

    # the user has (ostensibly) authenticated with the application, now
    # the access token can be fetched
    _logger.log('[' + __name__ + '] discord spy callback received',_logger.LogLevel.INFO)

    oauth_session = OAuth2Session(
        client_id=client_id,
        state=session.get('oauth2_state'),
        redirect_uri=redirect,
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
        _logger.log('[' + __name__ + '] unable to fetch discord access token: {0}'.format(error),_logger.LogLevel.ERROR)
        return('ERROR: ' + str(error))

    # store our new shiny access token in the spy token database

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
    query = 'INSERT INTO SpyTokens (accessToken, refreshToken, validUntil, TokenType) VALUES (%s, %s, %s, %s)'

    try:
        row = cursor.execute(
            query, (
                atoken['access_token'],
                atoken['refresh_token'],
                atoken['expires_at'],
                'discord',
            )
        )
        sql_conn.commit()
    except Exception as errmsg:
        _logger.log('[' + __name__ + '] mysql error: ' + str(errmsg), _logger.LogLevel.ERROR)
        return('MySQL error :(')
    finally:
        cursor.close()
        sql_conn.close()

    _logger.log('[' + __name__ + '] new discord spy inserted',_logger.LogLevel.INFO)
    return('ALL DONE!')
