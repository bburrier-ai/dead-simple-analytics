import hashlib
from urllib.parse import urlparse
from uuid import UUID

from sqlalchemy.engine import Connection

from config.settings import settings
from core.exceptions import ForbiddenError, NotFoundError, RateLimitError
from core.live import live_hub
from core.rate_limit import SlidingWindowRateLimiter
from db.repositories.events import EventsRepository
from db.repositories.sites import SitesRepository

_collect_ip_limiter = SlidingWindowRateLimiter()
_collect_site_limiter = SlidingWindowRateLimiter()


class CollectService:
    def __init__(self) -> None:
        self.sites = SitesRepository()
        self.events = EventsRepository()

    def ingest(
        self,
        conn: Connection,
        payload: dict,
        *,
        client_ip: str | None,
        user_agent: str | None,
        origin: str | None,
        referer: str | None,
    ) -> None:
        site_key = (payload.get("site_key") or "").strip()
        if not site_key:
            raise ForbiddenError("Missing site_key")

        site = self.sites.get_by_site_key(conn, site_key)
        if not site:
            raise NotFoundError("Unknown site")

        self._check_origin(site.get("allowed_domains") or [], origin, referer)
        ip_hash = self._hash_ip(client_ip)
        self._rate_limit(site_key, ip_hash)

        event_type = (payload.get("type") or "").strip()
        if event_type not in {"pageview", "click", "hover"}:
            raise ForbiddenError("Invalid event type")

        event_id = self._normalize_event_id(payload.get("event_id"))
        visitor_id = self._clip(payload.get("visitor_id"), 64) or None
        visitor_hash = self._normalize_visitor_hash(payload.get("visitor_hash"))
        session_id = self._clip(payload.get("session_id"), 64) or None

        inserted = self.events.insert(
            conn,
            {
                "site_id": site["id"],
                "event_id": event_id,
                "type": event_type,
                "path": self._clip(payload.get("path"), 512),
                "title": self._clip(payload.get("title"), 512),
                "track_id": self._clip(payload.get("track_id"), 128) or None,
                "referrer": self._clip(payload.get("referrer"), 1024) or None,
                "visitor_id": visitor_id,
                "visitor_hash": visitor_hash,
                "session_id": session_id,
                "ip_hash": ip_hash,
                "country": None,
                "region": None,
                "city": None,
                "user_agent": self._clip(user_agent, 512) or None,
            },
        )
        if not inserted:
            return

        live_hub.publish({"site_id": str(site["id"])})

    def _clip(self, value: object | None, max_len: int) -> str:
        text = "" if value is None else str(value)
        return text[:max_len]

    def _normalize_event_id(self, value: object | None) -> str:
        raw = self._clip(value, 36)
        try:
            return str(UUID(raw))
        except ValueError as exc:
            raise ForbiddenError("Invalid event_id") from exc

    def _normalize_visitor_hash(self, value: object | None) -> str | None:
        raw = self._clip(value, 64).lower()
        if not raw:
            return None
        if len(raw) == 64 and all(ch in "0123456789abcdef" for ch in raw):
            return raw
        if len(raw) <= 64 and raw.startswith("f_"):
            return raw
        return None

    def _hash_ip(self, ip: str | None) -> str:
        raw = (ip or "unknown") + settings.ip_hash_salt
        return hashlib.sha256(raw.encode()).hexdigest()

    def _rate_limit(self, site_key: str, ip_hash: str) -> None:
        if not _collect_ip_limiter.allow(
            f"ip:{site_key}:{ip_hash}",
            limit=settings.collect_rate_limit_per_min,
            window_sec=60.0,
        ):
            raise RateLimitError()
        if not _collect_site_limiter.allow(
            f"site:{site_key}",
            limit=settings.collect_site_rate_limit_per_min,
            window_sec=60.0,
        ):
            raise RateLimitError()

    def _check_origin(
        self,
        allowed_domains: list[str],
        origin: str | None,
        referer: str | None,
    ) -> None:
        host = self._host_from_header(origin) or self._host_from_header(referer)
        if not host:
            raise ForbiddenError("Missing Origin/Referer")
        normalized = [d.strip().lower() for d in allowed_domains if d.strip()]
        if not normalized:
            raise ForbiddenError("Site has no allowed domains")
        for domain in normalized:
            if host == domain or host.endswith(f".{domain}"):
                return
        raise ForbiddenError("Origin not allowed")

    def _host_from_header(self, value: str | None) -> str | None:
        if not value:
            return None
        parsed = urlparse(value)
        return (parsed.hostname or "").lower() or None
