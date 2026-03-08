from enum import Enum
import aiohttp
import asyncio
import dotenv

from config_handler import get_config
#from json_file_formatter import tu_mamma_morta


class Link(Enum):
    #async_scraper.py sync_scraper.py????
    #Scraper ogni 6 ore
    CUTOFF= "https://www.replays.lol/cutoff/{Region}/{cutoff_type}"

    #Scrape/fetch ogni 5 minuti
    LOLPROS_INGPRO = "https://api.lolpros.gg/lol/game/{lolpros_uuid}"
    RIOT_PLAYERSTATS = "https://{Region}.api.riotgames.com/lol/league/v4/entries/by-puuid/{uuid}?api_key={apikey}"
    OPGG_CURRENT_RANK = "https://op.gg/it/lol/summoners/{Region}/{Ign}-{Tag}"

    #Scraper ogni minuto
    RIOT_IS_IN_GAME = "https://{region}.api.riotgames.com/lol/spectator/v5/active-games/by-summoner/{uuid}?api_key={apikey}"

    def format(self, *args, **kwargs):
        return self.value.format(*args, **kwargs)

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
    await asyncio.gather(scrape_cutoff())
