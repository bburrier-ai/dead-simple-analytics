import secrets
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.engine import Connection


class SitesRepository:
    def list_for_user(self, conn: Connection, user_id: UUID) -> list[dict]:
        rows = conn.execute(
            text(
                """
                SELECT id, name, site_key, allowed_domains, active, created_at
                FROM sites
                WHERE user_id = :user_id
                ORDER BY created_at DESC
                """
            ),
            {"user_id": user_id},
        ).mappings()
        return [dict(r) for r in rows]

    def get_by_id(self, conn: Connection, site_id: UUID, user_id: UUID) -> dict | None:
        row = (
            conn.execute(
                text(
                    """
                SELECT id, name, site_key, allowed_domains, active, created_at
                FROM sites
                WHERE id = :id AND user_id = :user_id
                """
                ),
                {"id": site_id, "user_id": user_id},
            )
            .mappings()
            .first()
        )
        return dict(row) if row else None

    def get_by_site_key(self, conn: Connection, site_key: str) -> dict | None:
        row = (
            conn.execute(
                text(
                    """
                SELECT id, user_id, name, site_key, allowed_domains, active
                FROM sites
                WHERE site_key = :site_key AND active = TRUE
                """
                ),
                {"site_key": site_key},
            )
            .mappings()
            .first()
        )
        return dict(row) if row else None

    def insert(
        self,
        conn: Connection,
        user_id: UUID,
        name: str,
        allowed_domains: list[str],
    ) -> dict:
        site_key = f"sk_{secrets.token_urlsafe(16)}"
        return self._insert_row(conn, user_id, name, site_key, allowed_domains)

    def update(
        self,
        conn: Connection,
        site_id: UUID,
        user_id: UUID,
        name: str,
        site_key: str,
        allowed_domains: list[str],
    ) -> dict | None:
        row = (
            conn.execute(
                text(
                    """
                UPDATE sites
                SET name = :name,
                    site_key = :site_key,
                    allowed_domains = :allowed_domains
                WHERE id = :id AND user_id = :user_id
                RETURNING id, name, site_key, allowed_domains, active, created_at
                """
                ),
                {
                    "id": site_id,
                    "user_id": user_id,
                    "name": name,
                    "site_key": site_key,
                    "allowed_domains": allowed_domains,
                },
            )
            .mappings()
            .first()
        )
        return dict(row) if row else None

    def site_key_in_use(
        self, conn: Connection, site_key: str, exclude_id: UUID | None = None
    ) -> bool:
        row = conn.execute(
            text(
                """
                SELECT 1
                FROM sites
                WHERE site_key = :site_key
                  AND (:exclude_id IS NULL OR id <> :exclude_id)
                LIMIT 1
                """
            ),
            {"site_key": site_key, "exclude_id": exclude_id},
        ).first()
        return row is not None

    def _insert_row(
        self,
        conn: Connection,
        user_id: UUID,
        name: str,
        site_key: str,
        allowed_domains: list[str],
    ) -> dict:
        row = (
            conn.execute(
                text(
                    """
                INSERT INTO sites (user_id, name, site_key, allowed_domains)
                VALUES (:user_id, :name, :site_key, :allowed_domains)
                RETURNING id, name, site_key, allowed_domains, active, created_at
                """
                ),
                {
                    "user_id": user_id,
                    "name": name,
                    "site_key": site_key,
                    "allowed_domains": allowed_domains,
                },
            )
            .mappings()
            .one()
        )
        return dict(row)
