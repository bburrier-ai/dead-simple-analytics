import secrets

from fastapi import Request, Response

from config.settings import settings
from core.exceptions import ForbiddenError


def generate_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def set_csrf_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=settings.csrf_cookie_name,
        value=token,
        httponly=False,
        secure=settings.session_cookie_secure,
        samesite=settings.session_cookie_samesite,
        max_age=settings.jwt_expire_minutes * 60,
        path="/",
    )


def csrf_token_from_request(request: Request) -> str | None:
    return request.cookies.get(settings.csrf_cookie_name)


def validate_csrf(request: Request, *, form_token: str | None = None) -> None:
    cookie = csrf_token_from_request(request)
    header = request.headers.get("X-CSRF-Token")
    token = header or form_token
    if not cookie or not token or cookie != token:
        raise ForbiddenError("CSRF validation failed")
