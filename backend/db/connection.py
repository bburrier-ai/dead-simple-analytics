from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.pool import NullPool

from config.settings import settings


def create_db_engine(url: str | None = None) -> Engine:
    """Create a new SQLAlchemy engine (caller owns lifecycle)."""
    target = url or settings.database_url
    # Tests open many short-lived connections; NullPool avoids exhausting Postgres.
    kwargs: dict = {"pool_pre_ping": True}
    if settings.app_env == "test" or "5434" in target:
        kwargs["poolclass"] = NullPool
    else:
        kwargs["pool_size"] = 5
    return create_engine(target, **kwargs)


def check_db_connection(engine: Engine) -> bool:
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    return True


@contextmanager
def get_connection(engine: Engine) -> Generator[Connection, None, None]:
    with engine.begin() as conn:
        yield conn
