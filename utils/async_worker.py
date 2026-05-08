import asyncio
import dataclasses
import os
import re
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path

import aiohttp
from bs4 import BeautifulSoup
from dotenv import load_dotenv

from .config_handler import get_config
from .database import (
    get_all_users,
    reset_session_stats,
    update_cutoffs,
    update_in_game,
    update_player_stats,
)
from .logger_handler import LOGGER

env_path = Path(__file__).resolve().parent.parent / "Credential.env"
load_dotenv(dotenv_path=env_path)


_current_lp: dict[str, int] = {}
_session_start_lp: dict[str, int] = {}
_session_start_wins: dict[str, int] = {}
_session_start_losses: dict[str, int] = {}


class Link(Enum):
    CUTOFF = "https://www.replays.lol/cutoff/{Region}/{cutoff_type}"
    LOLPROS_INGAME = "https://api.lolpros.gg/lol/game/{lolpros_uuid}"
    RIOT_PLAYERSTATS = "https://{platform}.api.riotgames.com/lol/league/v4/entries/by-puuid/{uuid}?api_key={apikey}"
    OPGG_CURRENT_RANK = "https://op.gg/it/lol/summoners/{Region}/{Ign}-{Tag}"
    RIOT_IS_IN_GAME = "https://{platform}.api.riotgames.com/lol/spectator/v5/active-games/by-summoner/{uuid}?api_key={apikey}"

    def format(self, *args, **kwargs) -> str:
        return self.value.format(*args, **kwargs)


@dataclasses.dataclass
class ProPlayer:
    name: str
    role: str
    team: str


_lobby: list[ProPlayer] = []

_ROLE_MAP: dict[str, str] = {
    "TOP": "Top",
    "JUNGLE": "Jungle",
    "MIDDLE": "Mid",
    "MID": "Mid",
    "BOTTOM": "ADC",
    "BOT": "ADC",
    "ADC": "ADC",
    "UTILITY": "Support",
    "SUPPORT": "Support",
}


_PLATFORM_MAP: dict[str, str] = {
    "EUW": "euw1",
    "EUNE": "eun1",
    "NA": "na1",
    "KR": "kr",
    "BR": "br1",
    "JP": "jp1",
    "LAN": "la1",
    "LAS": "la2",
    "OCE": "oc1",
    "TR": "tr1",
    "RU": "ru",
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

_DIV_OFFSET: dict[str, int] = {"I": 75, "II": 50, "III": 25, "IV": 0}


def _platform_to_routing(region: str) -> str:
    return _PLATFORM_MAP.get(region.upper(), region.lower() + "1")


def _tier_to_elo(tier: str, division: str) -> int:
    return _TIER_BASE.get(tier.upper(), 0) + _DIV_OFFSET.get(division.upper(), 0)


async def scrape_cutoff() -> None:
    region = get_config(section="Details", value="riot_region")
    users = await get_all_users()
    if not users:
        LOGGER.warning("scrape_cutoff: nessun utente nel DB.")
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
                        "scrape_cutoff: nessun testo in CutoffAmount per %s",
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
                LOGGER.error("scrape_cutoff errore per %s: %s", cutoff_type, exc)

    if len(cutoffs) < 2:
        LOGGER.error("One or both cutoff values missing — skipping DB update.")
        return

    for user in users:
        await update_cutoffs(
            user.riot_uuid, cutoffs["challenger"], cutoffs["grandmaster"]
        )


async def fetch_riot_stats() -> None:
    platform = _platform_to_routing(get_config(section="Details", value="riot_region"))
    api_key = os.getenv("RIOT_API_KEY", "")
    users = await get_all_users()

    try:
        async with aiohttp.ClientSession() as session:
            for user in users:
                url = Link.RIOT_PLAYERSTATS.format(
                    platform=platform, uuid=user.riot_uuid, apikey=api_key
                )
                try:
                    async with session.get(url) as resp:
                        resp.raise_for_status()
                        entries: list[dict] = await resp.json()
                except Exception as exc:
                    LOGGER.error(
                        "fetch_riot_stats errore per %s: %s", user.riot_uuid, exc
                    )
                    continue

                ranked = next(
                    (e for e in entries if e.get("queueType") == "RANKED_SOLO_5x5"),
                    None,
                )
                if ranked is None:
                    LOGGER.info("Nessuna entry ranked solo per %s", user.riot_uuid)
                    continue

                lp: int = ranked["leaguePoints"]
                wins: int = ranked["wins"]
                losses: int = ranked["losses"]
                tier: str = ranked["tier"]
                div: str = ranked["rank"]

                prev_lp = _current_lp.get(user.riot_uuid, lp)
                lp_gain = lp - prev_lp
                _current_lp[user.riot_uuid] = lp

                session_start = _session_start_lp.setdefault(user.riot_uuid, lp)
                session_lp = lp - session_start

                total = wins + losses
                winrate = round(wins / total * 100) if total > 0 else 0
                elo = _tier_to_elo(tier, div)

                start_w = _session_start_wins.setdefault(user.riot_uuid, wins)
                start_l = _session_start_losses.setdefault(user.riot_uuid, losses)
                sess_w = max(0, wins - start_w)
                sess_l = max(0, losses - start_l)
                s_total = sess_w + sess_l
                sess_wr = round(sess_w / s_total * 100) if s_total > 0 else 0

                await update_player_stats(
                    user.riot_uuid,
                    win=wins,
                    losses=losses,
                    winrate=winrate,
                    lp_gain=lp_gain,
                    player_rank=f"{tier} {div}",
                    elo=elo,
                    session_wins=sess_w,
                    session_losses=sess_l,
                    session_winrate=sess_wr,
                    current_lp=lp,
                )

                from sqlalchemy import update as sa_update

                from .database import AsyncSessionLocal

                async with AsyncSessionLocal() as db:
                    await db.execute(
                        sa_update(user.__class__)
                        .where(user.__class__.riot_uuid == user.riot_uuid)
                        .values(session_lp=session_lp)
                    )
                    await db.commit()

                LOGGER.info(
                    "Stats updated for %s → %s %d LP (session_lp=%+d, lp_gain=%+d)",
                    user.riot_uuid,
                    f"{tier} {div}",
                    lp,
                    session_lp,
                    lp_gain,
                )
    except Exception as exc:
        LOGGER.error("fetch_riot_stats unexpected error: %s", exc)


async def fetch_lolpros_ingame() -> None:
    global _lobby
    users = [u for u in await get_all_users() if u.lolpros_uuid]
    if not users:
        return

    try:
        async with aiohttp.ClientSession() as session:
            for user in users:
                url = Link.LOLPROS_INGAME.format(lolpros_uuid=user.lolpros_uuid)
                try:
                    async with session.get(url) as resp:
                        if resp.status in (204, 404):
                            _lobby = []
                            LOGGER.debug(
                                "lolpros: %s non in game (HTTP %d)",
                                user.lolpros_uuid,
                                resp.status,
                            )
                            continue
                        resp.raise_for_status()
                        data: dict = await resp.json()
                        LOGGER.debug("lolpros raw response: %s", data)

                        participants: list[dict] = data.get("participants", [])
                        parsed: list[ProPlayer] = []

                        for p in participants:
                            team_raw = p.get("teamId", p.get("team", 100))
                            if isinstance(team_raw, int):
                                team = "blue" if team_raw == 100 else "red"
                            else:
                                team = (
                                    "blue"
                                    if str(team_raw).lower() in ("blue", "1", "100")
                                    else "red"
                                )

                            position_raw = str(
                                p.get("position", p.get("role", p.get("lane", "?")))
                            ).upper()
                            role = _ROLE_MAP.get(
                                position_raw, position_raw.capitalize()
                            )

                            player_info = p.get("player", p.get("pro", p))
                            name = str(
                                player_info.get("name", player_info.get("ign", "?"))
                                if isinstance(player_info, dict)
                                else player_info
                            )

                            if name and name != "?":
                                parsed.append(
                                    ProPlayer(name=name, role=role, team=team)
                                )

                        _lobby = parsed
                        LOGGER.info("Lobby aggiornata: %d pro trovati", len(_lobby))

                except Exception as exc:
                    LOGGER.error(
                        "fetch_lolpros_ingame errore per %s: %s", user.lolpros_uuid, exc
                    )
    except Exception as exc:
        LOGGER.error("fetch_lolpros_ingame unexpected error: %s", exc)


def get_lobby() -> list[ProPlayer]:
    return _lobby


# async def scrape_opgg() -> None:
#    """Scrape OP.GG (ogni 5 min). Placeholder — parsing HTML non implementato."""
#    region = get_config(section="Details", value="riot_region")
#    ign    = get_config(section="Details", value="riot_ign")
#    tag    = get_config(section="Details", value="riot_tag")
#    url    = Link.OPGG_CURRENT_RANK.format(Region=region, Ign=ign, Tag=tag)
#
#    try:
#        async with aiohttp.ClientSession(headers={"User-Agent": "Mozilla/5.0"}) as session:
#            async with session.get(url) as resp:
#                LOGGER.warning("scrape_opgg: HTTP %d per %s (parsing non implementato)", resp.status, url)
#                # TODO: parse global_rank dalla pagina OP.GG
#    except Exception as exc:
#        LOGGER.error("scrape_opgg errore: %s", exc)


async def fetch_is_in_game() -> None:
    platform = _platform_to_routing(get_config(section="Details", value="riot_region"))
    api_key = os.getenv("RIOT_API_KEY", "")
    users = await get_all_users()

    try:
        async with aiohttp.ClientSession() as session:
            for user in users:
                url = Link.RIOT_IS_IN_GAME.format(
                    platform=platform, uuid=user.riot_uuid, apikey=api_key
                )
                try:
                    async with session.get(url) as resp:
                        if resp.status == 200:
                            await update_in_game(user.riot_uuid, True)
                            LOGGER.info("%s è IN GAME", user.riot_uuid)
                        elif resp.status == 404:
                            await update_in_game(user.riot_uuid, False)
                        else:
                            LOGGER.error(
                                "fetch_is_in_game: status inatteso %d per %s",
                                resp.status,
                                user.riot_uuid,
                            )
                except Exception as exc:
                    LOGGER.error(
                        "fetch_is_in_game errore per %s: %s", user.riot_uuid, exc
                    )
    except Exception as exc:
        LOGGER.error("fetch_is_in_game unexpected error: %s", exc)


async def _reset_session() -> None:
    users = await get_all_users()
    for user in users:
        uid = user.riot_uuid
        _session_start_lp[uid] = _current_lp.get(uid, user.current_lp or 0)
        _session_start_wins[uid] = user.win or 0
        _session_start_losses[uid] = user.losses or 0
        await reset_session_stats(uid)
    LOGGER.info("Session stats resettate a mezzanotte.")


async def _loop_at_midnight(fn) -> None:
    while True:
        now = datetime.now()
        midnight = (now + timedelta(days=1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        wait = (midnight - now).total_seconds()
        LOGGER.info("Prossimo reset sessione in %.0f s.", wait)
        await asyncio.sleep(wait)
        await fn()


async def _loop(fn, interval: float) -> None:
    while True:
        await fn()
        await asyncio.sleep(interval)


async def scraper_worker() -> None:
    await start_tasks()


async def start_tasks() -> None:
    await asyncio.gather(
        _loop(scrape_cutoff, 6 * 600),
        _loop(
            lambda: asyncio.gather(
                fetch_riot_stats(),
                fetch_lolpros_ingame(),
                # scrape_opgg(),
            ),
            120,
        ),
        _loop(fetch_is_in_game, 5),
        _loop_at_midnight(_reset_session),
    )
