from enum import Enum

# sovereign token for tri discord


leadership_token = 'MjkwMTQ0MzMxOTY3MjM0MDU4.C6Wq7Q.c5B4veLpSStSafrC94WBb3UNUyo'
social_token = 'MzQ1MzkzMjA0Nzg0MjY3MjY1.DlzaAw.9I1hZcD6MGY7sqleu8yDnwe9Ta0'

class Channel(Enum):
    # a helpful enum because who the fuck knows what numbers mean
    ping_forwarding = 288786919175749632
    counterintel = 341589867840405524
    everyone = 269993133268271106
    tri_administration = 269997361827151872
    notification_spam = 396667297277935628
    pings = 432273498476380170

# oauth stuff for discord registration
# not currently the same as sovereign

client_id = '345393204784267265'
client_secret = 'BGS-7JHC_iD757AEveHf1piesG0SDiPh'
base_url = 'https://discordapp.com/api/v6'
redirect_url = 'https://auth.triumvirate.rocks/discord/callback?server_type=discord'
