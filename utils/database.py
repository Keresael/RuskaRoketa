import os
from pathlib import Path

import dotenv
from sqlalchemy import Boolean, Integer, String, select, text, update
from sqlalchemy.dialects.mysql import insert
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from .logger_handler import LOGGER

_env_path = Path(__file__).resolve().parent.parent / "Credential.env"
dotenv.load_dotenv(dotenv_path=_env_path)

DB_USER: str = os.getenv("DB_USER", "root")
DB_PASSWORD: str = os.getenv("DB_PASSWORD", "")
DB_HOST: str = os.getenv("DB_HOST", "localhost")
DB_NAME: str = os.getenv("DB_NAME", "RuskaRoketa")

DATABASE_URL = f"mysql+aiomysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}"
_BASE_URL = f"mysql+aiomysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}"


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    riot_uuid: Mapped[str] = mapped_column(String(255), primary_key=True)
    lolpros_uuid: Mapped[str | None] = mapped_column(
        String(255), unique=True, nullable=True
    )
    twitch_broadcaster_id: Mapped[str | None] = mapped_column(String(50), nullable=True)

    win: Mapped[int] = mapped_column(Integer, default=0)
    losses: Mapped[int] = mapped_column(Integer, default=0)
    winrate: Mapped[int | None] = mapped_column(Integer, nullable=True)
    current_lp: Mapped[int] = mapped_column(Integer, default=0)

    session_wins: Mapped[int] = mapped_column(Integer, default=0)
    session_losses: Mapped[int] = mapped_column(Integer, default=0)
    session_winrate: Mapped[int | None] = mapped_column(Integer, nullable=True)
    session_lp: Mapped[int] = mapped_column(Integer, default=0)

    lp_gain: Mapped[int | None] = mapped_column(Integer, nullable=True)
    player_rank: Mapped[str | None] = mapped_column(String(50), nullable=True)
    elo: Mapped[int | None] = mapped_column(Integer, nullable=True)
    global_rank: Mapped[int | None] = mapped_column(Integer, nullable=True)

    in_game: Mapped[bool] = mapped_column(Boolean, default=False)

    cutoff_chall: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cutoff_gm: Mapped[int | None] = mapped_column(Integer, nullable=True)


engine = create_async_engine(DATABASE_URL, echo=False, pool_pre_ping=True)
AsyncSessionLocal = async_sessionmaker(
    engine, expire_on_commit=False, class_=AsyncSession
)


async def init_db() -> None:
    temp_engine = create_async_engine(_BASE_URL, echo=False)
    try:
        async with temp_engine.connect() as conn:
            await conn.execute(text(f"CREATE DATABASE IF NOT EXISTS `{DB_NAME}`"))
            await conn.commit()
        LOGGER.info(f"Ensured database '{DB_NAME}' exists.")
    except Exception as exc:
        LOGGER.error(f"Could not create database '{DB_NAME}': {exc}")
        raise
    finally:
        await temp_engine.dispose()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    LOGGER.info("All tables created (or already exist).")


async def upsert_user(
    riot_uuid: str,
    lolpros_uuid: str | None = None,
    twitch_broadcaster_id: str | None = None,
) -> None:
    stmt = (
        insert(User)
        .values(
            riot_uuid=riot_uuid,
            lolpros_uuid=lolpros_uuid,
            twitch_broadcaster_id=twitch_broadcaster_id,
        )
        .on_duplicate_key_update(
            lolpros_uuid=lolpros_uuid,
            twitch_broadcaster_id=twitch_broadcaster_id,
        )
    )
    async with AsyncSessionLocal() as session:
        await session.execute(stmt)
        await session.commit()
    LOGGER.info("Upserted user riot_uuid=%s", riot_uuid)


async def get_all_users() -> list[User]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User))
        return list(result.scalars().all())


async def update_player_stats(
    riot_uuid: str,
    *,
    win: int | str | None,
    losses: int | str | None,
    winrate: int | str | None,
    lp_gain: int | str | None,
    player_rank: int | str | None,
    elo: int | str | None,
    session_wins: int | str | None,
    session_losses: int | str | None,
    session_winrate: int | str | None,
    current_lp: int | str | None,
) -> None:
    values = {
        k: v
        for k, v in {
            "win": win,
            "losses": losses,
            "winrate": winrate,
            "lp_gain": lp_gain,
            "player_rank": player_rank,
            "elo": elo,
            "session_wins": session_wins,
            "session_losses": session_losses,
            "session_winrate": session_winrate,
            "current_lp": current_lp,
        }.items()
        if v is not None
    }
    if not values:
        return

    stmt = update(User).where(User.riot_uuid == riot_uuid).values(**values)
    async with AsyncSessionLocal() as session:
        await session.execute(stmt)
        await session.commit()


async def update_in_game(riot_uuid: str, in_game: bool) -> None:
    stmt = update(User).where(User.riot_uuid == riot_uuid).values(in_game=in_game)
    async with AsyncSessionLocal() as session:
        await session.execute(stmt)
        await session.commit()


async def update_cutoffs(riot_uuid: str, cutoff_chall: int, cutoff_gm: int) -> None:
    stmt = (
        update(User)
        .where(User.riot_uuid == riot_uuid)
        .values(cutoff_chall=cutoff_chall, cutoff_gm=cutoff_gm)
    )
    async with AsyncSessionLocal() as session:
        await session.execute(stmt)
        await session.commit()


async def close_db() -> None:
    await engine.dispose()
    LOGGER.info("Database connection pool closed.")


async def get_cutoffs() -> tuple[int | None, int | None]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User.cutoff_chall, User.cutoff_gm))
        row = result.first()
        if row is None:
            return None, None
        return row.cutoff_chall, row.cutoff_gm


async def get_player_stats() -> User | None:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User))
        return result.scalars().first()


async def reset_session_stats(riot_uuid: str) -> None:
    async with AsyncSessionLocal() as session:
        await session.execute(
            update(User)
            .where(User.riot_uuid == riot_uuid)
            .values(session_wins=0, session_losses=0, session_winrate=0, session_lp=0)
        )
        await session.commit()
    LOGGER.info("Session stats resettate per %s", riot_uuid)


async def get_broadcaster_id() -> str | None:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User.twitch_broadcaster_id)
            .where(User.twitch_broadcaster_id.is_not(None))
            .where(User.twitch_broadcaster_id != "")
            .limit(1)
        )
        return result.scalar_one_or_none()
