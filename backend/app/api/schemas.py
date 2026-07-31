from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from core.models import CollectPayload, EventType


class LoginRequest(BaseModel):
    # No password-policy constraints here: login must not leak internal requirements
    # to unauthenticated clients (e.g. min length). Policy is enforced when setting passwords.
    username: str = ""
    password: str = ""


class UserResponse(BaseModel):
    id: str
    username: str


class SiteCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    allowed_domains: list[str] = Field(min_length=1)


class SiteUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    allowed_domains: list[str] = Field(min_length=1)
    site_key: str = Field(min_length=3, max_length=64)


class CollectEvent(BaseModel):
    """HTTP transport DTO for /collect. Converts to CollectPayload for the service."""

    event_id: str = Field(min_length=36, max_length=36)
    site_key: str
    type: EventType
    path: str = ""
    title: str = ""
    referrer: str = ""
    visitor_id: str = ""
    visitor_hash: str = ""
    session_id: str = ""
    track_id: str | None = None
    screen_w: int | None = None
    screen_h: int | None = None
    language: str | None = None

    @field_validator("event_id")
    @classmethod
    def validate_event_id(cls, value: str) -> str:
        try:
            UUID(value)
        except ValueError as exc:
            raise ValueError("event_id must be a UUID") from exc
        return value

    def to_payload(self) -> CollectPayload:
        return CollectPayload(
            event_id=UUID(self.event_id),
            site_key=self.site_key,
            type=self.type,
            path=self.path,
            title=self.title,
            referrer=self.referrer,
            visitor_id=self.visitor_id,
            visitor_hash=self.visitor_hash,
            session_id=self.session_id,
            track_id=self.track_id,
        )
