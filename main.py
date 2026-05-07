import asyncio
import logging
import os
from pathlib import Path

import twitchio
from dotenv import load_dotenv
from twitchio import eventsub
from twitchio.ext import commands

from utils.async_scraper import start_tasks
from utils.database import close_db, get_cutoffs, get_player_stats
from utils.logger_handler import LOGGER
from utils.song_handler import get_song
from utils.sync_scraper import startup

env_path = Path(__file__).resolve().parent / "Credential.env"
load_dotenv(dotenv_path=env_path)


class Bot(commands.Bot):
    def __init__(self) -> None:
        super().__init__(
            client_id=os.getenv("TWITCH_ID"),
            client_secret=os.getenv("TWITCH_SECRET"),
            bot_id="1157269116",
            owner_id="605131495",
            prefix="!",
        )

    async def setup_hook(self) -> None:
        # il value Twitch Brodcaster deve essere recuperato facendo una query in #Sync_Scraper
        payload = eventsub.ChatMessageSubscription(
            broadcaster_user_id="131070633", user_id=self.bot_id
        )
        await self.subscribe_websocket(payload=payload)

        await self.add_component(Commands(self))
        LOGGER.info("Finished setup hook!")


class Commands(commands.Component):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot

    @commands.command()
    async def help(self, ctx: commands.Context) -> None:
        await ctx.reply("!song, !cutoff <gm/chall>, !clip <clip title>, !rank")

    @commands.command(aliases=["musica", "spotify"])
    async def song(self, ctx: commands.Context) -> None:
        song = get_song()
        if song is None:
            await ctx.reply("No song currently playing")
        else:
            await ctx.reply(f"{song.title} - {song.artist}")

    @commands.command()
    async def tracklist(self, ctx: commands.Context) -> None:
        await ctx.reply("Non ho voglia di finirlo adesso domani faccio")

    @commands.command()
    async def cutoff(self, ctx: commands.Context, *, message: str = "") -> None:
        msg = message.lower().strip()

        if msg in ("gm", "grandmaster", "gmaster"):
            _, gm = await get_cutoffs()
            value = f"{gm} LP" if gm is not None else "dato non disponibile"
            await ctx.reply(f"Cutoff Grandmaster (EUW): {value}")

        elif msg in ("ch", "chall", "challenger"):
            chall, _ = await get_cutoffs()
            value = f"{chall} LP" if chall is not None else "dato non disponibile"
            await ctx.reply(f"Cutoff Challenger (EUW): {value}")

        else:
            await ctx.reply(
                "Rank non trovato — usa: !cutoff grandmaster  oppure  !cutoff challenger"
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

    # @commands.command()
    # async def lobby(self, ctx: commands.Context) -> None:
    #    await ctx.reply("Non ho voglia di finirlo adesso domani faccio")

    # @commands.command()
    # async def session(self, ctx: commands.Context) -> None:
    #    await ctx.reply("")

    # @commands.command()
    # async def autobet(self, ctx: commands.Context) -> None:
    #    await ctx.reply("")


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
