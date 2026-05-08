import asyncio
import os

import aiohttp

from .database import get_broadcaster_id, get_player_stats
from .logger_handler import LOGGER

_active_prediction_id: str | None = None
_autobet_task: asyncio.Task | None = None


async def _twitch_request(
    method: str, url: str, token: str, client_id: str, **kwargs
) -> dict | None:
    headers = {
        "Authorization": f"Bearer {token}",
        "Client-Id": client_id,
        "Content-Type": "application/json",
    }
    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.request(method, url, headers=headers, **kwargs) as resp:
            if resp.status in (200, 201):
                return await resp.json()
            LOGGER.error(
                "Twitch API %s %s → %d: %s", method, url, resp.status, await resp.text()
            )
            return None


async def create_prediction(
    broadcaster_id: str, token: str, client_id: str
) -> tuple[str, str, str] | None:
    data = await _twitch_request(
        "POST",
        "https://api.twitch.tv/helix/predictions",
        token,
        client_id,
        json={
            "broadcaster_id": broadcaster_id,
            "title": "autobet",
            "outcomes": [{"title": "win"}, {"title": "lose"}],
            "prediction_window": 60,
        },
    )
    if not data:
        return None
    pred = data["data"][0]
    outcomes = pred["outcomes"]
    win_id = next(o["id"] for o in outcomes if o["title"].lower() == "win")
    lose_id = next(o["id"] for o in outcomes if o["title"].lower() == "lose")
    return pred["id"], win_id, lose_id


async def lock_prediction(
    prediction_id: str, broadcaster_id: str, token: str, client_id: str
) -> None:
    await _twitch_request(
        "PATCH",
        "https://api.twitch.tv/helix/predictions",
        token,
        client_id,
        json={
            "broadcaster_id": broadcaster_id,
            "id": prediction_id,
            "status": "LOCKED",
        },
    )


async def cancel_prediction(
    prediction_id: str, broadcaster_id: str, token: str, client_id: str
) -> None:
    await _twitch_request(
        "PATCH",
        "https://api.twitch.tv/helix/predictions",
        token,
        client_id,
        json={
            "broadcaster_id": broadcaster_id,
            "id": prediction_id,
            "status": "CANCELED",
        },
    )


async def start_autobet(ctx) -> None:
    global _active_prediction_id, _autobet_task

    player = await get_player_stats()
    if player is None or not player.in_game:
        await ctx.reply("Il player non è in game, impossibile aprire la bet.")
        return

    await ctx.send("🎲 Autobet in arrivo!")
    await asyncio.sleep(1)
    await ctx.send("🎲 Pronto...")
    await asyncio.sleep(1)
    await ctx.send("🎲 BET APERTA! Hai 60 secondi per votare: Win o Lose!")

    broadcaster_id = await get_broadcaster_id()
    token = os.getenv("TWITCH_TOKEN", "")
    client_id = os.getenv("TWITCH_ID", "")

    result = await create_prediction(broadcaster_id or "", token, client_id)
    if result is None:
        await ctx.send("❌ Errore nell'aprire la bet.")
        return

    prediction_id, _, _ = result
    _active_prediction_id = prediction_id

    async def _monitor() -> None:
        global _active_prediction_id
        try:
            while True:
                await asyncio.sleep(15)
                p = await get_player_stats()
                if p is None or not p.in_game:
                    await lock_prediction(
                        prediction_id, broadcaster_id or "", token, client_id
                    )
                    await ctx.send(
                        "🔒 Partita finita — bet chiusa! Risolvi manualmente su Twitch."
                    )
                    _active_prediction_id = None
                    break
        except asyncio.CancelledError:
            pass

    _autobet_task = asyncio.create_task(_monitor())


async def stop_autobet(ctx) -> None:
    global _active_prediction_id, _autobet_task

    if _active_prediction_id is None:
        await ctx.reply("Nessuna bet attiva.")
        return

    if _autobet_task and not _autobet_task.done():
        _autobet_task.cancel()

    broadcaster_id = await get_broadcaster_id()
    token = os.getenv("TWITCH_TOKEN", "")
    client_id = os.getenv("TWITCH_ID", "")

    await cancel_prediction(
        _active_prediction_id, broadcaster_id or "", token, client_id
    )
    _active_prediction_id = None
    await ctx.send("❌ Bet annullata.")
