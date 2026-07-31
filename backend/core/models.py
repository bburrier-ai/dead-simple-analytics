"""Domain models shared across services and repositories."""

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class EventType(StrEnum):
    pageview = "pageview"
    click = "click"
    hover = "hover"
    custom = "custom"


class User(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: UUID
    username: str
    password_hash: str | None = Field(default=None, exclude=True)


class Site(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: UUID
    name: str
    site_key: str
    allowed_domains: list[str] = Field(default_factory=list)
    active: bool = True
    created_at: datetime | None = None
    snippet: str | None = None


class EventRecord(BaseModel):
    """Normalized event row ready for persistence."""

    site_id: UUID
    event_id: UUID
    type: EventType
    path: str = ""
    title: str = ""
    track_id: str | None = None
    referrer: str | None = None
    visitor_id: str | None = None
    visitor_hash: str | None = None
    session_id: str | None = None
    ip_hash: str
    country: str | None = None
    region: str | None = None
    city: str | None = None
    user_agent: str | None = None

    def to_db_params(self) -> dict:
        data = self.model_dump()
        data["type"] = self.type.value
        data["event_id"] = str(self.event_id)
        return data


class CollectPayload(BaseModel):
    """Validated collect body after HTTP transport parsing."""

    event_id: UUID
    site_key: str
    type: EventType
    path: str = ""
    title: str = ""
    referrer: str = ""
    visitor_id: str = ""
    visitor_hash: str = ""
    session_id: str = ""
    track_id: str | None = None
