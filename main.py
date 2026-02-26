import asyncio
import logging
import os

import twitchio
from twitchio import eventsub
from twitchio.ext import commands

from pathlib import Path
from dotenv import load_dotenv

from utils.song_handler import get_song

LOGGER: logging.Logger = logging.getLogger("Bot")
env_path = Path(__file__).resolve().parent / "Credential.env"
load_dotenv(dotenv_path=env_path)


class Bot(commands.Bot):

    def __init__(self) -> None:
        super().__init__(client_id=os.getenv("TWITCH_ID"), client_secret=os.getenv("TWITCH_SECRET"), bot_id="1157269116", owner_id="605131495", prefix="!")


    async def setup_hook(self) -> None:

        payload = eventsub.ChatMessageSubscription(broadcaster_user_id="131070633", user_id=self.bot_id)
        await self.subscribe_websocket(payload=payload)

        await self.add_component(Commands(self))
        LOGGER.info("Finished setup hook!")

class Commands(commands.Component):

    def __init__(self, bot: Bot) -> None:
        self.bot = bot

    @commands.command()
    async def help(self, ctx: commands.Context) -> None:
        await ctx.reply(f"Comandi disponibili: !song, !tracklist, !cutoff, !lobby, !clip, !rank")

    @commands.command(aliases=["musica"])
    async def song(self, ctx: commands.Context) -> None:
        song = get_song()
        if song is None:
            await ctx.reply("Nessuna canzone in riproduzione")
        else:
            await ctx.reply(f"{song.title} - {song.artist}")

    @commands.command()
    async def tracklist(self, ctx: commands.Context) -> None:
        await ctx.reply(f"Non ho voglia di finirlo adesso domani faccio")

    @commands.command()
    async def cutoff(self, ctx: commands.Context, *, message: str) -> None:
        await ctx.reply(f"{message}")

    @commands.command()
    async def clip(self, ctx: commands.Context) -> None:
        await ctx.reply(f"Non ho voglia di finirlo adesso domani faccio")

    #@commands.command()
    #async def rank(self, ctx: commands.Context) -> None:
    #    await ctx.reply(f"Non ho voglia di finirlo adesso domani faccio")

    @commands.command()
    async def lobby(self, ctx: commands.Context) -> None:
        await ctx.reply(f"Non ho voglia di finirlo adesso domani faccio")

def main() -> None:
    twitchio.utils.setup_logging(level=logging.INFO)

    async def runner() -> None:
        # 1. Avviamo i loop del "data_cacher" come task in background prima di bloccare il flusso.
        asyncio.create_task(start_cutoff_tasks())

        async with Bot() as bot:
            # 2. bot.start() è un'operazione che blocca l'esecuzione (gira all'infinito finché il bot è vivo)
            # Qualsiasi codice DOPO bot.start() non verrà MAI eseguito normalmente fino allo spegnimento del bot.
            await bot.start(os.getenv("TWITCH_TOKEN"))




    asyncio.run(runner())



main()