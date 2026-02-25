from __future__ import annotations

from typing import Generator

from sqlmodel import SQLModel, Session, create_engine

from ai.settings import settings


def _build_engine():
    url = settings.db_url or "sqlite:///mother_trades.db"
    connect_args = {}
    if url.startswith("sqlite"):
        connect_args = {"check_same_thread": False}
    return create_engine(url, connect_args=connect_args)


engine = _build_engine()


def init_db() -> None:
    from db import models  # noqa: F401

    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
