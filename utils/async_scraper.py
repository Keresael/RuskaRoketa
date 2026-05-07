import asyncio
import os
import re
from enum import Enum
from pathlib import Path

import aiohttp
import dotenv
from bs4 import BeautifulSoup

from .config_handler import get_config
from .database import (
    get_all_users,
    update_cutoffs,
    update_in_game,
    update_player_stats,
)
from .logger_handler import LOGGER

_env_path = Path(__file__).resolve().parent.parent / "Credential.env"
dotenv.load_dotenv(dotenv_path=_env_path)


class Link(Enum):
    # Scraped every 6 hours
    CUTOFF = "https://www.replays.lol/cutoff/{Region}/{cutoff_type}"

    # Fetched every 5 minutes
    LOLPROS_INGPRO = "https://api.lolpros.gg/lol/game/{lolpros_uuid}"
    RIOT_PLAYERSTATS = (
        "https://{Region}.api.riotgames.com/lol/league/v4/entries/"
        "by-puuid/{uuid}?api_key={apikey}"
    )
    OPGG_CURRENT_RANK = "https://op.gg/it/lol/summoners/{Region}/{Ign}-{Tag}"

    # Fetched every minute
    RIOT_IS_IN_GAME = (
        "https://{region}.api.riotgames.com/lol/spectator/v5/"
        "active-games/by-summoner/{uuid}?api_key={apikey}"
    )

    def format(self, *args, **kwargs) -> str:
        return self.value.format(*args, **kwargs)


_PLATFORM_MAP: dict[str, str] = {
    "EUW": "euw1",
    "EUNE": "eun1",
    "NA": "na1",
    "KR": "kr",
    "JP": "jp1",
    "BR": "br1",
    "LAN": "la1",
    "LAS": "la2",
    "OCE": "oc1",
    "TR": "tr1",
    "RU": "ru",
    "ME": "me1",
    "SG": "sg2",
    "PH": "ph2",
    "TW": "tw2",
    "VN": "vn2",
    "TH": "th2",
}

_TIER_BASE: dict[str, int] = {
    "IRON": 0,
    "BRONZE": 400,
    "SILVER": 800,
    "GOLD": 1200,
    "PLATINUM": 1600,
    "EMERALD": 2000,
    "DIAMOND": 2400,
    "MASTER": 2800,
    "GRANDMASTER": 2900,
    "CHALLENGER": 3000,
}

_DIVISION_OFFSET: dict[str, int] = {"I": 75, "II": 50, "III": 25, "IV": 0}


def _platform_to_routing(region: str) -> str:
    return _PLATFORM_MAP.get(region.upper(), region.lower() + "1")


async def scrape_cutoff() -> None:
    region = get_config(section="Details", value="riot_region")
    users = await get_all_users()
    if not users:
        LOGGER.warning("scrape_cutoff: no users in DB, skipping.")
        return

    cutoffs: dict[str, int] = {}

    async with aiohttp.ClientSession(headers={"User-Agent": "Mozilla/5.0"}) as session:
        for cutoff_type in ("challenger", "grandmaster"):
            url = f"https://www.replays.lol/cutoff/{region}/{cutoff_type}"
            try:
                async with session.get(url) as resp:
                    resp.raise_for_status()
                    html = await resp.text()

                soup = BeautifulSoup(html, "html.parser")

                h2 = soup.select_one('h2[class*="CutoffAmount"]')
                if h2 is None:
                    LOGGER.error(
                        "scrape_cutoff: elemento CutoffAmount non trovato per %s",
                        cutoff_type,
                    )
                    continue

                direct_text = h2.find(string=True, recursive=False)
                if not direct_text:
                    LOGGER.error(
                        "scrape_cutoff: nessun testo diretto in CutoffAmount per %s",
                        cutoff_type,
                    )
                    continue

                match = re.search(r"(\d+)", direct_text)
                if not match:
                    LOGGER.error(
                        "scrape_cutoff: impossibile parsare LP da '%s'", direct_text
                    )
                    continue

                cutoffs[cutoff_type] = int(match.group(1))
                LOGGER.info(
                    "Cutoff %s/%s = %d LP", region, cutoff_type, cutoffs[cutoff_type]
                )

            except Exception as exc:
                LOGGER.error("scrape_cutoff error per %s: %s", cutoff_type, exc)

    if len(cutoffs) < 2:
        LOGGER.error("One or both cutoff values missing — skipping DB update.")
        return

    for user in users:
        await update_cutoffs(
            user.riot_uuid, cutoffs["challenger"], cutoffs["grandmaster"]
        )


async def fetch_riot_stats() -> None:
    riot_region = get_config(section="Details", value="riot_region")
    platform = _platform_to_routing(riot_region)
    api_key = os.getenv("RIOT_API_KEY")

    try:
        users = await get_all_users()
        async with aiohttp.ClientSession() as session:
            for user in users:
                try:
                    url = Link.RIOT_PLAYERSTATS.format(
                        Region=platform,
                        uuid=user.riot_uuid,
                        apikey=api_key,
                    )
                    async with session.get(url) as response:
                        response.raise_for_status()
                        entries: list[dict] = await response.json()

                    solo_entry = next(
                        (e for e in entries if e["queueType"] == "RANKED_SOLO_5x5"),
                        None,
                    )
                    if solo_entry is None:
                        LOGGER.info(
                            f"No solo/duo entry for {user.riot_uuid} — skipping."
                        )
                        continue

                    wins: int = solo_entry["wins"]
                    losses: int = solo_entry["losses"]
                    lp: int = solo_entry["leaguePoints"]
                    tier: str = solo_entry["tier"]
                    rank_division: str = solo_entry["rank"]

                    player_rank = f"{tier} {rank_division}"
                    total_games = wins + losses
                    winrate = round(wins / total_games * 100) if total_games > 0 else 0

                    lp_gain: int = lp - (user.current_lp or 0)

                    win_delta = wins - (user.win or 0)
                    loss_delta = losses - (user.losses or 0)
                    session_wins = (
                        user.session_wins + win_delta
                        if win_delta > 0
                        else user.session_wins
                    )
                    session_losses = (
                        user.session_losses + loss_delta
                        if loss_delta > 0
                        else user.session_losses
                    )
                    session_total = session_wins + session_losses
                    session_winrate = (
                        round(session_wins / session_total * 100)
                        if session_total > 0
                        else 0
                    )

                    elo = _TIER_BASE.get(tier.upper(), 0) + _DIVISION_OFFSET.get(
                        rank_division.upper(), 0
                    )

                    await update_player_stats(
                        user.riot_uuid,
                        win=wins,
                        losses=losses,
                        winrate=winrate,
                        lp_gain=lp_gain,
                        player_rank=player_rank,
                        elo=elo,
                        session_wins=session_wins,
                        session_losses=session_losses,
                        session_winrate=session_winrate,
                        current_lp=lp,
                    )
                    LOGGER.info(
                        f"Stats updated for {user.riot_uuid}: "
                        f"{player_rank}, LP={lp}, W/L={wins}/{losses}."
                    )
                except Exception as exc:
                    LOGGER.error(f"Error fetching stats for {user.riot_uuid}: {exc}")
    except Exception as exc:
        LOGGER.error(f"Error in fetch_riot_stats: {exc}")


async def fetch_lolpros_ingame() -> None:
    users = [u for u in await get_all_users() if u.lolpros_uuid]
    if not users:
        return

    try:
        async with aiohttp.ClientSession() as session:
            for user in users:
                url = Link.LOLPROS_INGPRO.format(lolpros_uuid=user.lolpros_uuid)
                try:
                    async with session.get(url) as resp:
                        if resp.status in (204, 404):
                            LOGGER.debug(
                                "lolpros: %s not in game (HTTP %d)",
                                user.lolpros_uuid,
                                resp.status,
                            )
                            continue
                        resp.raise_for_status()
                        LOGGER.info(
                            "lolpros in-game data for %s: %s",
                            user.lolpros_uuid,
                            await resp.json(),
                        )
                except Exception as exc:
                    LOGGER.error(
                        "Error fetching lolpros in-game for %s: %s",
                        user.lolpros_uuid,
                        exc,
                    )
    except Exception as exc:
        LOGGER.error("fetch_lolpros_ingame unexpected error: %s", exc)


async def scrape_opgg() -> None:
    try:
        riot_region = get_config(section="Details", value="riot_region")
        riot_ign = get_config(section="Details", value="riot_ign")
        riot_tag = get_config(section="Details", value="riot_tag")

        url = Link.OPGG_CURRENT_RANK.format(
            Region=riot_region, Ign=riot_ign, Tag=riot_tag
        )
        headers = {"User-Agent": "Mozilla/5.0"}

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                LOGGER.warning(
                    f"OP.GG scraping is a best-effort placeholder. "
                    f"HTTP status: {response.status} for URL: {url}"
                )
    except Exception as exc:
        LOGGER.error(f"Error in scrape_opgg: {exc}")


async def fetch_is_in_game() -> None:
    riot_region = get_config(section="Details", value="riot_region")
    platform = _platform_to_routing(riot_region)
    api_key = os.getenv("RIOT_API_KEY")

    try:
        users = await get_all_users()
        async with aiohttp.ClientSession() as session:
            for user in users:
                try:
                    url = Link.RIOT_IS_IN_GAME.format(
                        region=platform,
                        uuid=user.riot_uuid,
                        apikey=api_key,
                    )
                    async with session.get(url) as response:
                        if response.status == 200:
                            await update_in_game(user.riot_uuid, True)
                            LOGGER.info(f"{user.riot_uuid} is currently in game.")
                        elif response.status == 404:
                            await update_in_game(user.riot_uuid, False)
                        else:
                            LOGGER.error(
                                f"Unexpected status {response.status} "
                                f"while checking in-game for {user.riot_uuid}."
                            )
                except Exception as exc:
                    LOGGER.error(
                        f"Error checking in-game status for {user.riot_uuid}: {exc}"
                    )
    except Exception as exc:
        LOGGER.error(f"Error in fetch_is_in_game: {exc}")


async def _loop(fn, interval: float) -> None:
    while True:
        await fn()
        await asyncio.sleep(interval)


async def scraper_worker() -> None:
    await start_tasks()


async def start_tasks() -> None:
    await asyncio.gather(
        _loop(scrape_cutoff, 6 * 3600),
        _loop(
            lambda: asyncio.gather(
                fetch_riot_stats(),
                fetch_lolpros_ingame(),
                scrape_opgg(),
                fetch_is_in_game(),
            ),
            60,
        ),
    )
