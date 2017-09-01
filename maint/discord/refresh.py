# refresh a discord api token

def refresh_token(old_rtoken):

    from requests_oauthlib import OAuth2Session
    import oauthlib.oauth2
    import common.credentials.discord as _discord
    import common.logger as _logger

    client_id = _discord.client_id
    client_secret = _discord.client_secret
    redirect_url = _discord.redirect_url

    token_url = base_url + '/oauth2/token'
    base_auth_url = base_url + '/oauth2/authorize'

    extra = {
        'client_id': client_id,
        'client_secret': client_secret,
    }

    discord = OAuth2Session(
        client_id=client_id,
        token=old_rtoken,
    )
    try:
        result = discord.refresh_token(
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
