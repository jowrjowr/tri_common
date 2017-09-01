# refresh an eve api token

def refresh_token(old_rtoken):

    from requests_oauthlib import OAuth2Session
    import oauthlib.oauth2
    import common.credentials.eve as _eve
    import common.logger as _logger

    base_url = 'https://login.eveonline.com'
    token_url = base_url + '/oauth/token'
    base_auth_url = base_url + '/oauth/authorize'
    redirect = _eve.redirect_url

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
        # there are a rather large amount of exceptions

        exception_type = type(error).__name__
        return exception_type, error

    return result, True
