from enum import Enum
import aiohttp
import asyncio
import dotenv

from config_handler import get_config
#from json_file_formatter import tu_mamma_morta


class Link(Enum):
    #Scrape/fetch on startup
    LOLPROS_UUID = "https://api.lolpros.gg/es/profiles/{lolpros_ign}"
    RIOT_PUUID = "https://{region}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{Ign}/{Tag}?api_key={apikey}"
    TWITCH_BRODCASTER = "https://decapi.me/twitch/id/{Twitch_Ign}"
    #async_scraper.py sync_scraper.py????
    #Scraper ogni 6 ore
    CUTOFF_GM = "https://www.replays.lol/cutoff/EUW/grandmaster"
    CUTOFF_CH = "https://www.replays.lol/cutoff/EUW/challenger"

    #Scrape/fetch ogni 5 minuti
    LOLPROS_INGPRO = "https://api.lolpros.gg/lol/game/{lolpros_uuid}"
    RIOT_PLAYERSTATS = "https://{Region}.api.riotgames.com/lol/league/v4/entries/by-puuid/{uuid}?api_key={apikey}"
    OPGG_CURRENT_RANK = "https://op.gg/it/lol/summoners/{Region}/{Ign}-{Tag}"

    #Scraper ogni minuto
    RIOT_IS_IN_GAME = "https://{region}.api.riotgames.com/lol/spectator/v5/active-games/by-summoner/{uuid}?api_key={apikey}"

    def format(self, *args, **kwargs):
        return self.value.format(*args, **kwargs)

async def fetch_twitch():
    pass

async def scrape_cutoff():
    pass

async def fetch_riot():
    pass

async def fetch_lolpros():
    pass

#fetch solo perche sono pigro potrei calcolare
async def scrape_opgg():
    pass

async def scraper_worker():
    pass

async def start_tasks():
    pass
    #metodino per fare il join di tutti gli async
    #await asyncio.gather()
