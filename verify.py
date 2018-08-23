from jose import jwt

def verify(token):

    # pull data out of JWT token
    # for ESI, deliberately not doing full validation due to trusting the source
    # also its a pain in the ass

    print(token)

    try:
        data = jwt.get_unverified_claims(token)
    except Exception as e:
        return False

    _, _, charid = data['sub'].split(':')
    charid = int(charid)
    charname = data['name']
    scopes = data['scp']

    return charid, charname, scopes
