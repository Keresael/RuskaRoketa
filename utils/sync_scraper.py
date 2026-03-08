from enum import Enum


class Link(Enum):
    LOLPROS_UUID = "https://api.lolpros.gg/es/profiles/{lolpros_ign}"
    RIOT_PUUID = "https://{region}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{Ign}/{Tag}?api_key={apikey}"
    TWITCH_BRODCASTER = "https://decapi.me/twitch/id/{Twitch_Ign}"


def fetch_twitch():
    pass

def fetch_lolpros():
    pass

def fetch_riot():
    pass
