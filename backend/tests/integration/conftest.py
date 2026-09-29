from collections.abc import Iterator
from pathlib import Path

import pytest
from sqlalchemy.orm import Session, sessionmaker

from tts.store.db import make_engine, make_session_factory, upgrade


@pytest.fixture
def db_url(tmp_path: Path) -> str:
    """A migrated database: a temporary SQLite file, or PostgreSQL when `TT_TEST_PG` is set."""
    import os

    url = os.environ.get("TT_TEST_PG") or f"sqlite:///{tmp_path / 'tts.db'}"
    if url.startswith("postgres"):
        from sqlalchemy import text

        engine = make_engine(url)
        with engine.begin() as conn:
            conn.execute(text("DROP SCHEMA public CASCADE"))
            conn.execute(text("CREATE SCHEMA public"))
        engine.dispose()
    upgrade(url)
    return url


@pytest.fixture
def session_factory(db_url: str) -> sessionmaker[Session]:
    return make_session_factory(make_engine(db_url))


@pytest.fixture
def session(session_factory: sessionmaker[Session]) -> Iterator[Session]:
    with session_factory() as s:
        yield s
