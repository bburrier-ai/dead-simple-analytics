import re
from uuid import UUID

from sqlalchemy.engine import Connection

from config.settings import settings
from core.exceptions import AppError, NotFoundError
from db.repositories.sites import SitesRepository

SITE_KEY_RE = re.compile(r"^sk_[A-Za-z0-9_-]+$")


class SitesService:
    def __init__(self) -> None:
        self.repo = SitesRepository()

    def list_sites(self, conn: Connection, user_id: UUID) -> list[dict]:
        return self.repo.list_for_user(conn, user_id)

    def create_site(
        self,
        conn: Connection,
        user_id: UUID,
        name: str,
        allowed_domains: list[str],
    ) -> dict:
        domains = self._normalize_domains(allowed_domains)
        site = self.repo.insert(conn, user_id, name.strip(), domains)
        site["snippet"] = self.snippet_for(site["site_key"])
        return site

    def update_site(
        self,
        conn: Connection,
        user_id: UUID,
        site_id: UUID,
        name: str,
        allowed_domains: list[str],
        site_key: str,
    ) -> dict:
        domains = self._normalize_domains(allowed_domains)
        normalized_key = self._normalize_site_key(site_key)
        if self.repo.site_key_in_use(conn, normalized_key, exclude_id=site_id):
            raise AppError("Site key is already in use")
        site = self.repo.update(
            conn,
            site_id,
            user_id,
            name.strip(),
            normalized_key,
            domains,
        )
        if not site:
            raise NotFoundError("Site not found")
        site["snippet"] = self.snippet_for(site["site_key"])
        return site

    def get_site(self, conn: Connection, user_id: UUID, site_id: UUID) -> dict:
        site = self.repo.get_by_id(conn, site_id, user_id)
        if not site:
            raise NotFoundError("Site not found")
        site["snippet"] = self.snippet_for(site["site_key"])
        return site

    def snippet_for(self, site_key: str) -> str:
        base = settings.public_base_url.rstrip("/")
        return (
            f'<script defer src="{base}/dsa.js" data-site="{site_key}"></script>'
        )

    def _normalize_domains(self, allowed_domains: list[str]) -> list[str]:
        domains = [d.strip().lower() for d in allowed_domains if d.strip()]
        if not domains:
            raise AppError("At least one allowed domain is required")
        return domains

    def _normalize_site_key(self, site_key: str) -> str:
        key = site_key.strip()
        if not SITE_KEY_RE.match(key):
            raise AppError("Site key must start with sk_ and use letters, numbers, _ or -")
        return key
