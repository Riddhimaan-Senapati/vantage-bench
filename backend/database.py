"""
database.py
-----------
SQLite engine + session factory.
Tables are created on first startup (via create_db_and_tables).
"""

import os
from pathlib import Path

from dotenv import load_dotenv
from sqlmodel import SQLModel, Session, create_engine

load_dotenv()

# Default: coverageiq.db in the same directory as this file
_DEFAULT_DB = f"sqlite:///{Path(__file__).parent / 'coverageiq.db'}"
DATABASE_URL: str = os.getenv("DATABASE_URL", _DEFAULT_DB)

# SQLite: connect_args disables the "same thread" restriction so FastAPI can
# share the connection across request threads.
_connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, echo=False, connect_args=_connect_args)


def create_db_and_tables() -> None:
    """Import all models so SQLModel.metadata is populated, then create tables."""
    import models  # noqa: F401 – side effect: registers all SQLModel tables
    SQLModel.metadata.create_all(engine)


def get_session():
    """FastAPI dependency that yields a DB session and closes it when done."""
    with Session(engine) as session:
        yield session
