import os
import requests

from enum import Enum
from dotenv import load_dotenv

from config_handler import get_config
from pathlib import Path

env_path = Path(__file__).resolve().parent.parent / "Credential.env"
load_dotenv(dotenv_path=env_path)

class Link(Enum):
    LOLPROS_UUID = "https://api.lolpros.gg/es/profiles/{lolpros_ign}"
    RIOT_PUUID = "https://{server}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{ign}/{tag}?api_key={apikey}"
    TWITCH_BRODCASTER = "https://decapi.me/twitch/id/{Twitch_Ign}"
    TWITCH_TOKEN_REFERSH = "https://twitchtokengenerator.com/api/refresh/{TOKEN_REFERSH}"

    def format(self, *args, **kwargs):
        return self.value.format(*args, **kwargs)

def fetch_twitch():
    brodcaster_id_rough = requests.get(Link.TWITCH_BRODCASTER.format(Twitch_Ign=get_config(section="Details", value="Twitch_Brodcaster")))
    brodcaster_id = brodcaster_id_rough.json()
    print(brodcaster_id)


def fetch_token():
    response = requests.get(Link.TWITCH_TOKEN_REFERSH.format(TOKEN_REFERSH=os.getenv("TWITCH_REFERSH_TOKEN")))
    token_rough = response.json()
    token = token_rough["access_token"]
    print(token)
    #with open("Credential.env", "w") as f:
    #    f.write(token)

def fetch_lolpros():
    response = requests.get(Link.LOLPROS_UUID.format(lolpros_ign=get_config(section="Details", value="lolpros_name")))
    lolpros_uuid_rough = response.json()
    lolpros_uuid = lolpros_uuid_rough["uuid"]
    print(lolpros_uuid)

def fetch_riot():
    response = requests.get(Link.RIOT_PUUID.format(server=get_config(section="Details", value="Riot_server"),ign=get_config(section="Details", value="riot_ign"),tag=get_config(section="Details", value="riot_tag"),apikey=os.getenv("RIOT_API_KEY")))
    riot_uuid_rough = response.json()
    riot_uuid = riot_uuid_rough["puuid"]
    print(riot_uuid)

if __name__ == "__main__":
    fetch_twitch()
    fetch_token()
    fetch_lolpros()
    fetch_riot()