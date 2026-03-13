import os
import requests
import functools

from enum import Enum
from dotenv import load_dotenv
from dotenv import set_key

from config_handler import get_config
from pathlib import Path
from logger_handler import LOGGER

env_path = Path(__file__).resolve().parent.parent / "Credential.env"
load_dotenv(dotenv_path=env_path)

class Link(Enum):
    LOLPROS_UUID = "https://api.lolpros.gg/es/profiles/{lolpros_ign}"
    RIOT_PUUID = "https://{server}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{ign}/{tag}?api_key={apikey}"
    TWITCH_BRODCASTER = "https://decapi.me/twitch/id/{Twitch_Ign}"
    TWITCH_TOKEN_REFERSH = "https://twitchtokengenerator.com/api/refresh/{TOKEN_REFERSH}"

    def format(self, *args, **kwargs):
        return self.value.format(*args, **kwargs)


def api_error_handler(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except requests.exceptions.HTTPError as e:
            LOGGER.error(f"HTTP Error in {func.__name__}: {e}")
            return None
        except requests.exceptions.RequestException as e:
            LOGGER.error(f"Network Error in {func.__name__}: {e}")
            return None
        except KeyError as e:
            LOGGER.error(f"Unexpected JSON structure in {func.__name__}. Missing key: {e}")
            return None
        except Exception as e:
            LOGGER.error(f"Unexpected system error in {func.__name__}: {e}")
            return None

    return wrapper

@api_error_handler
def fetch_twitch():
    url = Link.TWITCH_BRODCASTER.format(Twitch_Ign=get_config(section="Details", value="Twitch_Brodcaster"))
    with requests.get(url) as response:
        response.raise_for_status()
        brodcaster_id = response.json()

    print(brodcaster_id)

    return brodcaster_id

@api_error_handler
def fetch_token():
    url = Link.TWITCH_TOKEN_REFERSH.format(TOKEN_REFERSH=os.getenv("TWITCH_REFERSH_TOKEN"))
    with requests.get(url) as response:
        response.raise_for_status()
        token_rough = response.json()

    token = token_rough["access_token"]
    set_key(env_path,"TWITCH_TOKEN", token)


@api_error_handler
def fetch_lolpros():
    url = Link.LOLPROS_UUID.format(lolpros_ign=get_config(section="Details", value="lolpros_name")    )
    with requests.get(url) as response:
        response.raise_for_status()
        lolpros_uuid_rough = response.json()

    lolpros_uuid = lolpros_uuid_rough["uuid"]
    print(lolpros_uuid)

    return lolpros_uuid

@api_error_handler
def fetch_riot():
    url = Link.RIOT_PUUID.format(server=get_config(section="Details", value="Riot_server"),ign=get_config(section="Details", value="riot_ign"),tag=get_config(section="Details", value="riot_tag"),apikey=os.getenv("RIOT_API_KEY"))
    with requests.get(url) as response:
        response.raise_for_status()
        riot_uuid_rough = response.json()

    riot_uuid = riot_uuid_rough["puuid"]
    print(riot_uuid)

    return riot_uuid

if __name__ == "__main__":
    fetch_twitch()
    fetch_token()
    fetch_lolpros()
    fetch_riot()