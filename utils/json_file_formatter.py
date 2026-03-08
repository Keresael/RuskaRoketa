import dataclasses
import json
import os

import aiofiles
from dataclasses import asdict


@dataclasses.dataclass
class Stats:
    Winrate: int
    Win: int
    Losses: int
    Session_wins: int
    Session_losses: int
    Session_winrate: int
    Lp_gain: int
    Lp_losses: int
    Rank: str
    Elo: int
    Cutoff_chall: int
    Cutoff_gm: int
    Global_rank: int
    Lp: int
    Session_Lp: int


def create_json():
    with open('riot_stats.json', 'w') as f:
        f.write("{}")

async def update_json():
     if not os.path.exists('riot_stats.json'):
         create_json()

     async with aiofiles.open("riot_stats.json", 'w') as f:
         json_string = json.dumps(asdict(Stats), indent=4)
         await f.write(json_string)

async def get_json():
    pass

