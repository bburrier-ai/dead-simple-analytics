from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection, Engine

from config.settings import settings

_engine: Engine | None = None


def get_engine(url: str | None = None) -> Engine:
    global _engine
    target = url or settings.database_url
    if _engine is None or str(_engine.url) != target:
        _engine = create_engine(target, pool_pre_ping=True, pool_size=5)
    return _engine


def check_db_connection(engine: Engine | None = None) -> bool:
    eng = engine or get_engine()
    with eng.connect() as conn:
        conn.execute(text("SELECT 1"))
    return True


@contextmanager
def get_connection(url: str | None = None) -> Generator[Connection, None, None]:
    engine = get_engine(url)
    with engine.begin() as conn:
        yield conn
