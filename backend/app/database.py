from functools import lru_cache
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.config import get_settings


class Base(DeclarativeBase):
    pass


@lru_cache(maxsize=1)
def get_engine():
    settings = get_settings()
    engine = create_engine(
        f"sqlite:///{settings.db_path}",
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(conn, _record):
        conn.execute("PRAGMA foreign_keys = ON")

    return engine


@lru_cache(maxsize=1)
def get_session_factory():
    return sessionmaker(autocommit=False, autoflush=False, bind=get_engine())
