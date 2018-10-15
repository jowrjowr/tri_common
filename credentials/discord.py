from enum import Enum

# sovereign token for tri discord


leadership_token = 'MjkwMTQ0MzMxOTY3MjM0MDU4.C6Wq7Q.c5B4veLpSStSafrC94WBb3UNUyo'
social_token = 'MzQ1MzkzMjA0Nzg0MjY3MjY1.Dqa1iw.SlgauymZHbMr9100ndauRFzB898'

class Channel(Enum):
    # a helpful enum because who the fuck knows what numbers mean

    general = 432273498476380170
    supers = 501506421406564352
    administration = 501507311471296513
    skyteam = 501508052374257674
    skirmish = 501508105474146305
    notifications = 501506486996828201
    ping_forwarding = 501508332641714176

# oauth stuff for discord registration
# not currently the same as sovereign

client_id = '345393204784267265'
client_secret = 'BGS-7JHC_iD757AEveHf1piesG0SDiPh'
base_url = 'https://discordapp.com/api/v6'
redirect_url = 'https://auth.triumvirate.rocks/discord/callback?server_type=discord'
