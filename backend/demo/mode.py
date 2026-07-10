from fastapi import Request, Response

from config.settings import settings

COOKIE_NAME = "dsa_demo_mode"
COOKIE_ENABLED = "1"
COOKIE_DISABLED = "0"

_LOCAL_ENVS = {"local", "test", "development", "dev"}


def available(environment: str | None = None) -> bool:
    env = (environment if environment is not None else settings.app_env).strip().lower()
    return env in _LOCAL_ENVS


def default_enabled(environment: str | None = None) -> bool:
    env = (environment if environment is not None else settings.app_env).strip().lower()
    return env in {"local", "development", "dev"}


def enabled_from_request(request: Request, environment: str | None = None) -> bool:
    if not available(environment):
        return False
    cookie = request.cookies.get(COOKIE_NAME)
    if cookie is None:
        return default_enabled(environment)
    value = cookie.strip()
    if value == COOKIE_ENABLED:
        return True
    if value == COOKIE_DISABLED:
        return False
    return default_enabled(environment)


def set_mode_cookie(response: Response, enabled: bool, environment: str | None = None) -> None:
    env = (environment if environment is not None else settings.app_env).strip().lower()
    response.set_cookie(
        key=COOKIE_NAME,
        value=COOKIE_ENABLED if enabled else COOKIE_DISABLED,
        path="/",
        httponly=False,
        samesite="lax",
        secure=env not in _LOCAL_ENVS,
        max_age=60 * 60 * 24 * 30,
    )
