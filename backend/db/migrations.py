import logging
from pathlib import Path

from alembic.config import Config
from sqlalchemy import text

from alembic import command
from config.settings import settings
from db.connection import get_connection
from db.repositories.users import UsersRepository
from services.auth import AuthService

logger = logging.getLogger(__name__)
BACKEND_ROOT = Path(__file__).resolve().parents[1]


def run_migrations() -> None:
    cfg = Config(str(BACKEND_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_ROOT / "alembic"))
    cfg.set_main_option("sqlalchemy.url", settings.database_url)
    command.upgrade(cfg, "head")
    _seed_admin()


def _seed_admin() -> None:
    auth = AuthService()
    with get_connection() as conn:
        # Legacy installs renamed email→username but kept admin@example.com as the value.
        conn.execute(
            text(
                """
                UPDATE users
                SET username = :username
                WHERE username = 'admin@example.com'
                """
            ),
            {"username": settings.admin_username},
        )
        repo = UsersRepository()
        if repo.count(conn) > 0:
            return
        password_hash = auth.hash_password(settings.admin_password)
        repo.insert(conn, settings.admin_username, password_hash)
        logger.info("Seeded admin user", extra={"username": settings.admin_username})
