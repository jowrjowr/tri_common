from enum import Enum

# sovereign token for tri discord

token = 'MjkwMTQ0MzMxOTY3MjM0MDU4.C6Wq7Q.c5B4veLpSStSafrC94WBb3UNUyo'

class Channel(Enum):
    # a helpful enum because who the fuck knows what numbers mean
    ping_forwarding = 288786919175749632
    counterintel = 341589867840405524
    everyone = 269993133268271106
    tri_administration = 269997361827151872
    notification_spam = 396667297277935628

# oauth stuff for discord registration
# not currently the same as sovereign

client_id = '345393204784267265'
client_secret = 'zp31sVBvYop6boVIfQXNtcEv28fU4lPV'
base_url = 'https://discordapp.com/api/v6'
redirect_url = 'https://auth.triumvirate.rocks/discord/callback?server_type=discord'
