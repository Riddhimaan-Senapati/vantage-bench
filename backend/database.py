"""
database.py
-----------
SQLite engine + session factory.
Tables are created on first startup (via create_db_and_tables).
"""

import os
import sys
import urllib.parse
from pathlib import Path

from dotenv import load_dotenv
from sqlmodel import SQLModel, Session, create_engine

load_dotenv()

# Default: coverageiq.db in the same directory as this file
_DEFAULT_DB = f"sqlite:///{Path(__file__).parent / 'coverageiq.db'}"
# DB_URL takes priority — use this in DO App Platform to bypass the automatic
# database-attachment binding that controls DATABASE_URL.
DATABASE_URL: str = os.getenv("DB_URL") or os.getenv("DATABASE_URL", _DEFAULT_DB)

# Debug: log the first 40 chars of DATABASE_URL so we can see what was received
print(
    f"[db] DATABASE_URL received: {repr(DATABASE_URL[:40])}...",
    file=sys.stderr,
    flush=True,
)


def _build_engine_url(raw: str) -> str:
    """
    Return a SQLAlchemy-safe connection string.

    For PostgreSQL: strips surrounding quotes, normalises the scheme to
    postgresql+psycopg2, and URL-encodes the password so special characters
    (@, /, +, =) don't break the parser.
    For SQLite: returns the string unchanged.
    """
    raw = raw.strip().strip('"').strip("'")

    # Normalise postgres:// → postgresql+psycopg2://
    # and postgresql:// → postgresql+psycopg2://
    if raw.startswith("postgres://"):
        raw = "postgresql+psycopg2://" + raw[len("postgres://"):]
    elif raw.startswith("postgresql://"):
        raw = "postgresql+psycopg2://" + raw[len("postgresql://"):]

    if not raw.startswith("postgresql+"):
        return raw  # SQLite or other — leave untouched

    prefix = raw[: raw.index("://") + 3]  # e.g. "postgresql+psycopg2://"
    rest = raw[len(prefix):]               # "user:pass@host:port/db?params"

    # rfind('@') so passwords that contain '@' are handled correctly
    at_idx = rest.rfind("@")
    if at_idx == -1:
        return raw

    userinfo = rest[:at_idx]       # "user:pass"
    hostinfo = rest[at_idx + 1:]   # "host:port/db?sslmode=require"

    colon_idx = userinfo.find(":")
    if colon_idx == -1:
        return raw

    user = userinfo[:colon_idx]
    password = userinfo[colon_idx + 1:]

    encoded_password = urllib.parse.quote(password, safe="")
    return f"{prefix}{user}:{encoded_password}@{hostinfo}"


# SQLite: connect_args disables the "same thread" restriction so FastAPI can
# share the connection across request threads.
_connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

_engine_url = _build_engine_url(DATABASE_URL)
print(f"[db] engine URL scheme: {repr(_engine_url[:40])}...", file=sys.stderr, flush=True)

engine = create_engine(_engine_url, echo=False, connect_args=_connect_args)


def create_db_and_tables() -> None:
    """Import all models so SQLModel.metadata is populated, then create tables."""
    import models  # noqa: F401 – side effect: registers all SQLModel tables
    SQLModel.metadata.create_all(engine)


def get_session():
    """FastAPI dependency that yields a DB session and closes it when done."""
    with Session(engine) as session:
        yield session
