# refresh a discord api token

def refresh_token(old_rtoken):

    from requests_oauthlib import OAuth2Session

    import common.credentials.eve as _eve
    import common.logger as _logger
    import flask

    base_url = 'https://login.eveonline.com'
    token_url = base_url + '/oauth/token'
    base_auth_url = base_url + '/oauth/authorize'
    redirect = _eve.redirect

    extra = {
        'client_id': _eve.client_id,
        'client_secret': _eve.client_secret,
    }

    eve = OAuth2Session(
        client_id=_eve.client_id,
        token=old_rtoken,
    )
    try:
        result = eve.refresh_token(
            token_url,
            redirect_uri=redirect,
            refresh_token=old_rtoken,
            **extra,
        )
    except Exception as error:
        return error

    return result
