from enum import Enum
import aiohttp
import asyncio


class Link(Enum):
    #Scrape on startup
    LOLPROS_UUID = "https://api.lolpros.gg/es/profiles/{lolpros_ign}"
    RIOT_PUUID = "https://{region}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{ign}/{tag}?api_key={apikey}"

    #Scraper ogni 6 ore
    CUTOFF_GM = "https://www.replays.lol/cutoff/EUW/grandmaster"
    CUTOFF_CH = "https://www.replays.lol/cutoff/EUW/challenger"

    #Scraper ogni 5 minuti
    LOLPROS_DEIDARA = "https://api.lolpros.gg/lol/game/47c4a0dc-1d06-4360-bb3a-437630e34152"
    RIOT_PLAYERSTATS = "https://{region}.api.riotgames.com/lol/league/v4/entries/by-puuid/{uuid}?api_key={apikey}"
    OPGG_CURRENT_RANK = "https://op.gg/it/lol/summoners/{region}/{username}-{tag}"

    #Scraper ogni minuto
    RIOT_IS_IN_GAME = "https://{region}.api.riotgames.com/lol/spectator/v5/active-games/by-summoner/{uuid}?api_key={apikey}"

    def format(self, *args, **kwargs):
        return self.value.format(*args, **kwargs)


async def fetch_cutoff():
    pass

async def fetch_riot():
    pass

async def fetch_lolpros():
    pass

#fetch solo perche sono pigro potrei calcolare
async def fetch_opgg():
    pass

async def scraper_worker():
    pass

async def start_tasks():
    pass
    #metodino per fare il join di tutti gli async
    #await asyncio.gather()
