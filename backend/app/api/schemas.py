from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class LoginRequest(BaseModel):
    username: str = Field(min_length=1)
    password: str = Field(min_length=8)


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
    event_id: str = Field(min_length=36, max_length=36)
    site_key: str
    type: str
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
