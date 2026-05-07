import asyncio
import functools
import os
from enum import Enum
from pathlib import Path

import requests
from dotenv import load_dotenv, set_key

from .config_handler import get_config
from .database import close_db, init_db, upsert_user
from .logger_handler import LOGGER

env_path = Path(__file__).resolve().parent.parent / "Credential.env"
load_dotenv(dotenv_path=env_path)


class Link(Enum):
    LOLPROS_UUID = "https://api.lolpros.gg/es/profiles/{lolpros_ign}"
    RIOT_PUUID = (
        "https://{server}.api.riotgames.com/riot/account/v1/accounts/"
        "by-riot-id/{ign}/{tag}?api_key={apikey}"
    )
    TWITCH_BRODCASTER = "https://decapi.me/twitch/id/{Twitch_Ign}"
    TWITCH_TOKEN_REFERSH = (
        "https://twitchtokengenerator.com/api/refresh/{TOKEN_REFERSH}"
    )

    def format(self, *args, **kwargs) -> str:
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
            LOGGER.error(
                f"Unexpected JSON structure in {func.__name__}. Missing key: {e}"
            )
            return None
        except Exception as e:
            LOGGER.error(f"Unexpected system error in {func.__name__}: {e}")
            return None

    return wrapper


@api_error_handler
def fetch_twitch() -> str | None:
    url = Link.TWITCH_BRODCASTER.format(
        Twitch_Ign=get_config(section="Details", value="Twitch_Brodcaster")
    )
    with requests.get(url) as response:
        response.raise_for_status()
        broadcaster_id = response.text.strip()

    LOGGER.info("Twitch broadcaster ID: %s", broadcaster_id)
    return broadcaster_id


@api_error_handler
def fetch_token() -> None:
    url = Link.TWITCH_TOKEN_REFERSH.format(
        TOKEN_REFERSH=os.getenv("TWITCH_REFERSH_TOKEN")
    )
    with requests.get(url) as response:
        response.raise_for_status()
        token_rough = response.json()

    token = token_rough["access_token"]
    set_key(env_path, "TWITCH_TOKEN", token)
    LOGGER.info("Twitch access token refreshed and saved.")


@api_error_handler
def fetch_lolpros() -> str | None:
    url = Link.LOLPROS_UUID.format(
        lolpros_ign=get_config(section="Details", value="lolpros_name")
    )
    with requests.get(url) as response:
        response.raise_for_status()
        lolpros_uuid_rough = response.json()

    lolpros_uuid: str = lolpros_uuid_rough["uuid"]
    LOGGER.info(f"LolPros UUID: {lolpros_uuid}")
    return lolpros_uuid


@api_error_handler
def fetch_riot() -> str | None:
    url = Link.RIOT_PUUID.format(
        server=get_config(section="Details", value="Riot_server"),
        ign=get_config(section="Details", value="riot_ign"),
        tag=get_config(section="Details", value="riot_tag"),
        apikey=os.getenv("RIOT_API_KEY"),
    )
    with requests.get(url) as response:
        response.raise_for_status()
        riot_uuid_rough = response.json()

    riot_uuid: str = riot_uuid_rough["puuid"]
    LOGGER.info(f"Riot PUUID: {riot_uuid}")
    return riot_uuid


async def startup() -> None:
    try:
        fetch_twitch()
        fetch_token()

        lolpros_uuid = fetch_lolpros()
        riot_uuid = fetch_riot()

        if riot_uuid is None:
            LOGGER.error("startup: could not retrieve Riot PUUID — aborting DB seed.")
            return

        await init_db()
        await upsert_user(riot_uuid=riot_uuid, lolpros_uuid=lolpros_uuid)
        LOGGER.info("Startup complete — user seeded in DB.")
    finally:
        await close_db()


if __name__ == "__main__":
    asyncio.run(startup())
