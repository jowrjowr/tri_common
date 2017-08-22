# refresh a discord api token

def refresh_token(old_rtoken):

    from requests_oauthlib import OAuth2Session

    import common.credentials.discord as _discord
    import common.logger as _logger
    import flask

    base_url = 'https://discordapp.com/api'
    token_url = '/oauth2/token'
    base_auth_url = '/oauth2/authorize'
    redirect = 'https://auth.triumvirate.rocks/5eyes/callback?server_type=discord'

    extra = {
        'client_id': _discord.client_id,
        'client_secret': _discord.client_secret,
    }

    discord = OAuth2Session(
        client_id=_discord.client_id,
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
        return error

    return result
