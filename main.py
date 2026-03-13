import asyncio
import logging
import os

import twitchio
from twitchio import eventsub
from twitchio.ext import commands

from pathlib import Path
from dotenv import load_dotenv

from utils.logger_handler import LOGGER
from utils.song_handler import get_song


env_path = Path(__file__).resolve().parent / "Credential.env"
load_dotenv(dotenv_path=env_path)


class Bot(commands.Bot):

    def __init__(self) -> None:
        super().__init__(client_id=os.getenv("TWITCH_ID"), client_secret=os.getenv("TWITCH_SECRET"), bot_id="1157269116", owner_id="605131495", prefix="!")


    async def setup_hook(self) -> None:
        #il value Twitch Brodcaster deve essere recuperato facendo una query in #Sync_Scraper
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
        await ctx.reply(f"!song, !cutoff <gm/chall>, !clip <clip title> ")

    @commands.command(aliases=["musica"])
    async def song(self, ctx: commands.Context) -> None:
        song = get_song()
        if song is None:
            await ctx.reply("No song currently playing")
        else:
            await ctx.reply(f"{song.title} - {song.artist}")

    @commands.command()
    async def tracklist(self, ctx: commands.Context) -> None:
        await ctx.reply(f"Non ho voglia di finirlo adesso domani faccio")

    @commands.command()
    async def cutoff(self, ctx: commands.Context, *, message: str) -> None:
        if message == "gm" or message == "grandmaster" or message =="gmaster":
            #get_from_json(cutoff_grandmaster)
            await ctx.reply("")
        if message == "ch" or message == "chall" or message == "challenger":
            #get_from_json(cutoff_challenger)
            await ctx.reply("")
        else:
            await ctx.reply("Argument not found. Try with Challenger or GrandMaster")

    @commands.command()
    async def clip(self, ctx: commands.Context, *, title: str = None) -> None:
        if not title or title.isspace():
            await ctx.reply("Hey! You need to add a title to the clip.")
            return
        else:
            try:
                utenti = await ctx.bot.fetch_users(logins=[ctx.channel.name])

                if not utenti:
                    await ctx.send("Errore: impossibile trovare il canale.")
                    return

                streamer = utenti[0]

                clip = await streamer.create_clip(title=title, duration=60, token_for=os.getenv("TWITCH_TOKEN"))

                await ctx.reply(f"Clip created! Check it out here: {clip.edit_url}")

            except twitchio.HTTPException as e:
                await ctx.reply("Ops, I'm not able to create a clip right now.")
                LOGGER.error(e)
            except Exception as e:
                await ctx.reply("Ops, I'm not able to create a clip right now.")
                LOGGER.error(e)


    #@commands.command()
    #async def rank(self, ctx: commands.Context) -> None:
    #    await ctx.reply(f"Non ho voglia di finirlo adesso domani faccio")

    @commands.command()
    async def lobby(self, ctx: commands.Context) -> None:
        await ctx.reply(f"Non ho voglia di finirlo adesso domani faccio")

def main() -> None:
    LOGGER.setLevel(logging.INFO)
    #fetch_token()
    async def runner() -> None:
        #asyncio.create_task(start_tasks())


        async with Bot() as bot:
            await bot.start(os.getenv("TWITCH_TOKEN"))

    asyncio.run(runner())

main()