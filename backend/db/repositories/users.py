from uuid import UUID

from sqlalchemy import text
from sqlalchemy.engine import Connection


class UsersRepository:
    def count(self, conn: Connection) -> int:
        row = conn.execute(text("SELECT COUNT(*) FROM users")).scalar_one()
        return int(row)

    def get_by_username(self, conn: Connection, username: str) -> dict | None:
        row = (
            conn.execute(
                text("SELECT id, username, password_hash FROM users WHERE username = :username"),
                {"username": username},
            )
            .mappings()
            .first()
        )
        return dict(row) if row else None

    def get_by_id(self, conn: Connection, user_id: UUID) -> dict | None:
        row = (
            conn.execute(
                text("SELECT id, username FROM users WHERE id = :id"),
                {"id": user_id},
            )
            .mappings()
            .first()
        )
        return dict(row) if row else None

    def insert(self, conn: Connection, username: str, password_hash: str) -> dict:
        row = (
            conn.execute(
                text(
                    """
                INSERT INTO users (username, password_hash)
                VALUES (:username, :password_hash)
                RETURNING id, username
                """
                ),
                {"username": username, "password_hash": password_hash},
            )
            .mappings()
            .one()
        )
        return dict(row)
