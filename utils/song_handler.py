import dataclasses
import os
from pathlib import Path

import pylast

from dotenv import load_dotenv

env_path = Path(file).resolve().parent.parent / "Credential.env"
load_dotenv(dotenv_path=env_path)


@dataclasses.dataclass
class Song:
    title: str
    artist: str

def get_user() -> pylast.User:
    return pylast.LastFMNetwork(api_key=os.getenv("LASTFM_KEY"), api_secret=os.getenv("LASTFM_SECRET")).get_user("deidaralol")

def get_song() -> Song | None:
    user = get_user()
    track = user.get_now_playing()
    if track is None:
        return None
    return Song(track.title, track.artist.get_name())

if name == "main":
    song = get_song()
    print(song.title if song else "Nessuna canzone in riproduzione")