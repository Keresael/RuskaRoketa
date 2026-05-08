import asyncio
import logging
import os
from pathlib import Path

import twitchio
from dotenv import load_dotenv
from twitchio import eventsub
from twitchio.ext import commands

from utils.async_worker import get_lobby, start_tasks
from utils.autobet_helper import start_autobet, stop_autobet
from utils.database import close_db, get_cutoffs, get_player_stats
from utils.logger_handler import LOGGER
from utils.song_handler import get_song, get_tracklist
from utils.sync_worker import fetch_twitch, startup

env_path = Path(__file__).resolve().parent / "Credential.env"
load_dotenv(dotenv_path=env_path)


class Bot(commands.Bot):
    def __init__(self) -> None:
        client_id = os.getenv("TWITCH_ID")
        client_secret = os.getenv("TWITCH_SECRET")
        if not client_id or not client_secret:
            LOGGER.error("TWITCH_ID e/o TWITCH_SECRET mancanti nel .env")
            raise RuntimeError("TWITCH_ID e/o TWITCH_SECRET mancanti nel .env")
        super().__init__(
            client_id=client_id,
            client_secret=client_secret,
            bot_id="1157269116",
            owner_id="605131495",
            prefix="!",
        )

    async def setup_hook(self) -> None:
        payload = eventsub.ChatMessageSubscription(
            broadcaster_user_id=fetch_twitch(), user_id=self.bot_id
        )
        await self.subscribe_websocket(payload=payload)

        await self.add_component(Commands(self))
        LOGGER.info("Finito hook setup")


class Commands(commands.Component):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot

    @commands.command()
    async def help(self, ctx: commands.Context) -> None:
        await ctx.reply(
            "!song, !cutoff <gm/chall>, !clip <clip title>, !rank, !session"
        )

    @commands.command(aliases=["musica", "spotify"])
    async def song(self, ctx: commands.Context) -> None:
        song = get_song()
        if song is None:
            await ctx.reply("Nessuna traccia trovata.")
        else:
            await ctx.reply(f"{song.title} - {song.artist}")

    @commands.command()
    async def tracklist(self, ctx: commands.Context) -> None:
        tracks = await asyncio.to_thread(get_tracklist)
        if not tracks:
            await ctx.reply("Nessuna traccia recente trovata.")
            return
        reply = " | ".join(
            f"{i}. {s.title} - {s.artist}" for i, s in enumerate(tracks, start=1)
        )
        await ctx.reply(reply)

    @commands.command()
    async def cutoff(self, ctx: commands.Context, *, message: str = "") -> None:
        msg = message.lower().strip()

        if msg in ("gm", "grandmaster", "gmaster", "grandmasta"):
            _, gm = await get_cutoffs()
            value = f"{gm} LP" if gm is not None else "dato non disponibile"
            await ctx.reply(f"Cutoff Grandmaster (EUW): {value}")

        elif msg in ("ch", "chall", "challenger"):
            chall, _ = await get_cutoffs()
            value = f"{chall} LP" if chall is not None else "dato non disponibile"
            await ctx.reply(f"Cutoff Challenger (EUW): {value}")

        else:
            await ctx.reply(
                "Rank non trovato — usa: !cutoff  grandmasta   oppure  !cutoff challenger"
            )

    @commands.command()
    async def clip(self, ctx: commands.Context, *, title: str = " ") -> None:
        if not title or title.isspace():
            await ctx.reply("Hey! Devi aggiungere un titolo alla clip.")
            return
        else:
            try:
                utenti = await ctx.bot.fetch_users(logins=[ctx.channel.name])

                if not utenti:
                    await ctx.send("Errore: impossibile trovare il canale.")
                    return

                streamer = utenti[0]

                clip = await streamer.create_clip(
                    title=title, duration=60, token_for=os.getenv("TWITCH_TOKEN")
                )

                await ctx.reply(
                    f"Clip creata! Puoi vedere la clip qui: {clip.edit_url}"
                )

            except twitchio.HTTPException as e:
                await ctx.reply("Ops, impossibile creare la clip.")
                LOGGER.error(e)
            except Exception as e:
                await ctx.reply("Ops, impossibile creare la clip.")
                LOGGER.error(e)

    @commands.command()
    async def rank(self, ctx: commands.Context) -> None:
        player = await get_player_stats()

        if player is None or player.player_rank is None:
            await ctx.reply("Nessun dato disponibile.")
            return

        _RANK_EMOJI: dict[str, str] = {
            "IRON": "iron",
            "BRONZE": "bronze",
            "SILVER": "silver",
            "GOLD": "gold",
            "PLATINUM": "platinum",
            "EMERALD": "emerald",
            "DIAMOND": "diamond",
            "MASTER": "masta",
            "GRANDMASTER": "grandmasta",
            "CHALLENGER": "challenger",
        }

        tier = player.player_rank.split()[0].upper()
        label = _RANK_EMOJI.get(tier, tier.lower())

        lp = player.current_lp or 0
        wins = player.win or 0
        losses = player.losses or 0

        await ctx.reply(
            f"{label} {lp} LP | {wins}W {losses}L | {player.winrate or 0}% WR"
        )

    @commands.command()
    async def lobby(self, ctx: commands.Context) -> None:
        player = await get_player_stats()

        if player is None or not player.in_game:
            await ctx.reply("Non in game attualmente.")
            return

        pros = get_lobby()
        if not pros:
            await ctx.reply("Nessun pro rilevato in lobby.")
            return

        blue = [p for p in pros if p.team == "blue"]
        red = [p for p in pros if p.team == "red"]

        parts: list[str] = []
        if blue:
            parts.append("Blue: " + " | ".join(f"{p.name} ({p.role})" for p in blue))
        if red:
            parts.append("Red: " + " | ".join(f"{p.name} ({p.role})" for p in red))

        await ctx.reply("  ".join(parts))

    @commands.command()
    async def session(self, ctx: commands.Context) -> None:
        player = await get_player_stats()
        if player is None:
            await ctx.reply("Nessun dato disponibile.")
            return
        await ctx.reply(
            f"{player.session_wins}W {player.session_losses}L "
            f"| {player.session_winrate or 0}% WR "
            f"| {player.session_lp:+d} LP"
        )

    @commands.command()
    async def autobet(self, ctx: commands.Context, action: str = "") -> None:
        is_owner = str(ctx.author.id) == self.bot.owner_id
        is_mod = getattr(ctx.author, "is_mod", False)
        if not (is_owner or is_mod):
            await ctx.reply("Non hai i permessi per usare questo comando.")
            return

        match action.lower().strip():
            case "start":
                await start_autobet(ctx)
            case "stop":
                await stop_autobet(ctx)
            case _:
                await ctx.reply("Uso: !autobet start | !autobet stop")


def main() -> None:
    LOGGER.setLevel(logging.INFO)

    async def runner() -> None:
        try:
            await startup()

            async with Bot() as bot:
                await asyncio.gather(
                    bot.start(os.getenv("TWITCH_TOKEN")),
                    start_tasks(),
                )
        finally:
            await close_db()

    asyncio.run(runner())


main()
