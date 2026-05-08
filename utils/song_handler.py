import dataclasses
import os
from pathlib import Path

import pylast
from dotenv import load_dotenv

from .logger_handler import LOGGER

env_path = Path(__file__).resolve().parent.parent / "Credential.env"
load_dotenv(dotenv_path=env_path)


@dataclasses.dataclass
class Song:
    title: str
    artist: str


def get_user() -> pylast.User:
    api_key = os.getenv("LASTFM_KEY")
    api_secret = os.getenv("LASTFM_SECRET")
    if not api_key or not api_secret:
        raise RuntimeError("TWITCH_ID e/o TWITCH_SECRET mancanti nel .env")
    return pylast.LastFMNetwork(api_key=api_key, api_secret=api_secret).get_user(
        "deidaralol"
    )


def get_song() -> Song | None:
    user = get_user()
    track = user.get_now_playing()
    if track is None or track.artist is None:
        LOGGER.info("Nessuna canzone in riproduzione")
        return None
    return Song(str(track.title), str(track.artist.get_name()))


def get_tracklist() -> list[Song]:
    user = get_user()
    recent = user.get_recent_tracks(limit=5)
    return [
        Song(str(entry.track.title), str(entry.track.artist.get_name()))
        for entry in recent
        if entry.track is not None and entry.track.artist is not None
    ]


if __name__ == "main":
    song = get_song()
    print(song.title if song else "Nessuna canzone in riproduzione")
