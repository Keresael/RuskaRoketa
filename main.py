import asyncio
import logging
import os

import twitchio
from twitchio import eventsub
from twitchio.ext import commands

from pathlib import Path
from dotenv import load_dotenv

from utils.song_handler import get_song
from utils.config_handler import get_config
from utils.scraper import start_tasks, get_cutoff

LOGGER: logging.Logger = logging.getLogger("Bot")
env_path = Path(__file__).resolve().parent / "Credential.env"
load_dotenv(dotenv_path=env_path)


class Bot(commands.Bot):

    def __init__(self) -> None:
        super().__init__(client_id=os.getenv("TWITCH_ID"), client_secret=os.getenv("TWITCH_SECRET"), bot_id="1157269116", owner_id="605131495", prefix="!")


    async def setup_hook(self) -> None:
        #payload = eventsub.ChatMessageSubscription(broadcaster_user_id=get_config(section="Details", value="Twitch Brodcaster"), user_id=self.bot_id)
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
        if message is "gm" or message is "grandmaster" or message is "gmaster":
            #get_from_json(cutoff_grandmaster)
            await ctx.reply("")
        if message is "ch" or message is "chall" or message is "challenger":
            #get_from_json(cutoff_challenger)
            await ctx.reply("")
        else:
            await ctx.reply("Argomento non riconosciuto. Prova con Challenger o GrandMaster")

    @commands.command()
    async def clip(self, ctx: commands.Context, *, message: str) -> None:
        await ctx.reply(f"{message}")

    @commands.command()
    async def rank(self, ctx: commands.Context) -> None:
        await ctx.reply(f"Non ho voglia di finirlo adesso domani faccio")

    @commands.command()
    async def lobby(self, ctx: commands.Context) -> None:
        await ctx.reply(f"Non ho voglia di finirlo adesso domani faccio")

def main() -> None:
    twitchio.utils.setup_logging(level=logging.INFO)

    async def runner() -> None:
        asyncio.create_task(start_tasks())

        async with Bot() as bot:
            await bot.start(os.getenv("TWITCH_TOKEN"))

    asyncio.run(runner())



main()