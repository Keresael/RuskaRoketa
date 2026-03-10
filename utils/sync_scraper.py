from enum import Enum
import requests
from config_handler import get_config

class Link(Enum):
    LOLPROS_UUID = "https://api.lolpros.gg/es/profiles/{lolpros_ign}"
    RIOT_PUUID = "https://{region}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{Ign}/{Tag}?api_key={apikey}"
    TWITCH_BRODCASTER = "https://decapi.me/twitch/id/{Twitch_Ign}"
    TWITCH_TOKEN_REFERSH = " https://twitchtokengenerator.com/api/refresh/{TOKEN_REFERSH}"


def fetch_twitch():
    r = requests.get(Link.TWITCH_BRODCASTER.value)
    print(r.content)

def fetch_token():
    pass

def fetch_lolpros():
    pass

def fetch_riot():
    pass

if __name__ == "__main__":
    fetch_twitch()
    fetch_token()
    fetch_lolpros()
    fetch_riot()