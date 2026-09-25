# RUSKAROKETA

A Twitch chat bot for the League of Legends streamer
[deidxraa](https://www.twitch.tv/deidxraa). While the stream is live, viewers
can ask it about the current state of the game, the streamer's rank, the music
playing in the background, pro players in the lobby and more — all without
leaving chat.

## What it does

Built on [twitchio](https://github.com/twitchio/twitchio) (EventSub over a
WebSocket), the bot listens on the channel and answers commands prefixed with
`!`:

- **`!song`** — the track currently playing (artist and title).
- **`!tracklist`** — the streamer's recent tracks.
- **`!rank`** — current rank, tier, LP, win rate and recent W/L.
- **`!session`** — stats for the current game session (W/L, win rate, LP diff).
- **`!cutoff gm` / `!cutoff challenger`** — the current LP cutoff for
  Grandmaster / Challenger on EUW.
- **`!lobby`** — any pro player currently detected in the same game.
- **`!clip <title>`** — creates a clip of the ongoing stream with the given
  title.
- **`!help`** — lists the available commands.

## How it works

The bot never holds a single source of truth: it pulls live data from several
places and pieces it together on request.

- **Riot Games API** — the streamer's summoner data: rank, LP, win rate and
  session history.
- **Stat sites** (`op.gg`, `replays.lol`, `lolpros.gg`) — scraped for lobby
  detection and rank cutoff values.
- **Last.fm API** — the currently playing track and recent tracklist.

Requests are routed through an async worker that fetches and caches the data in
a local database, so repeated commands are fast and don't hammer the upstream
APIs. Twitch credentials and the Last.fm key live in `Credential.env` and
`config.ini` (gitignored, never committed).

## Project layout

| Path                     | Role                                            |
|--------------------------|-------------------------------------------------|
| `main.py`                | Bot entry point and chat commands              |
| `utils/async_worker.py`  | Async fetching (lobby, live data) and tasks    |
| `utils/sync_worker.py`   | Startup, Twitch user resolution                 |
| `utils/song_handler.py`  | Current song + tracklist from Last.fm           |
| `utils/database.py`      | Local cache / storage of queried data           |
| `utils/config_handler.py`| Reads `config.ini`                             |
| `utils/logger_handler.py`| Shared logging setup                           |