import hashlib
import re
from urllib.parse import urlparse

from sqlalchemy.engine import Engine

from config.settings import settings
from core.exceptions import ForbiddenError, NotFoundError, RateLimitError
from core.live import live_hub
from core.models import CollectPayload, EventRecord, Site
from core.rate_limit import SlidingWindowRateLimiter
from db.repositories.events import EventsRepository
from db.repositories.sites import SitesRepository

_collect_ip_limiter = SlidingWindowRateLimiter()
_collect_site_limiter = SlidingWindowRateLimiter()
_TRACK_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")


class CollectService:
    def __init__(self, engine: Engine | None = None) -> None:
        self._engine = engine
        self.sites = SitesRepository()
        self.events = EventsRepository()

    def ingest(
        self,
        payload: CollectPayload,
        *,
        client_ip: str | None,
        user_agent: str | None,
        origin: str | None,
        referer: str | None,
    ) -> None:
        site_key = payload.site_key.strip()
        if not site_key:
            raise ForbiddenError("Missing site_key")

        with self._require_engine().begin() as conn:
            site_row = self.sites.get_by_site_key(conn, site_key)
            if not site_row:
                raise NotFoundError("Unknown site")
            site = Site.model_validate(site_row)

            self._check_origin(site.allowed_domains, origin, referer)
            ip_hash = self._hash_ip(client_ip)
            self._rate_limit(site_key, ip_hash)

            event = EventRecord(
                site_id=site.id,
                event_id=payload.event_id,
                type=payload.type,
                path=self._clip(payload.path, 512),
                title=self._clip(payload.title, 512),
                track_id=self._normalize_track_id(payload.track_id),
                referrer=self._clip(payload.referrer, 1024) or None,
                visitor_id=self._clip(payload.visitor_id, 64) or None,
                visitor_hash=self._normalize_visitor_hash(payload.visitor_hash),
                session_id=self._clip(payload.session_id, 64) or None,
                ip_hash=ip_hash,
                country=None,
                region=None,
                city=None,
                user_agent=self._clip(user_agent, 512) or None,
            )
            inserted = self.events.insert(conn, event.to_db_params())

        if not inserted:
            return

        live_hub.publish({"site_id": str(site.id)})

    def _clip(self, value: object | None, max_len: int) -> str:
        text = "" if value is None else str(value)
        return text[:max_len]

    def _normalize_track_id(self, value: object | None) -> str | None:
        raw = self._clip(value, 128)
        if not raw or not _TRACK_ID_RE.fullmatch(raw):
            return None
        return raw

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

    def _require_engine(self) -> Engine:
        if self._engine is None:
            raise RuntimeError("CollectService requires a database engine")
        return self._engine
