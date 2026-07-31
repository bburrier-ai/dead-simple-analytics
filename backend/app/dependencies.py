from typing import Annotated
from uuid import UUID

from fastapi import Cookie, Depends, Request

from config.settings import settings
from core.exceptions import UnauthorizedError
from core.models import User
from demo import mode as demo_mode
from services.auth import AuthService
from services.collect import CollectService
from services.events import EventsService
from services.sites import SitesService
from services.stats import StatsService


def get_demo_mode(request: Request) -> bool:
    return demo_mode.enabled_from_request(request)


DemoMode = Annotated[bool, Depends(get_demo_mode)]


def get_auth_service(request: Request) -> AuthService:
    return request.app.state.auth_service


def get_collect_service(request: Request) -> CollectService:
    return request.app.state.collect_service


def get_sites_service(request: Request) -> SitesService:
    return request.app.state.sites_service


def get_events_service(request: Request) -> EventsService:
    return request.app.state.events_service


def get_stats_service(request: Request) -> StatsService:
    return request.app.state.stats_service


AuthSvc = Annotated[AuthService, Depends(get_auth_service)]
CollectSvc = Annotated[CollectService, Depends(get_collect_service)]
SitesSvc = Annotated[SitesService, Depends(get_sites_service)]
EventsSvc = Annotated[EventsService, Depends(get_events_service)]
StatsSvc = Annotated[StatsService, Depends(get_stats_service)]


def get_current_user_id(
    request: Request,
    auth: AuthSvc,
    session: str | None = Cookie(default=None, alias=settings.session_cookie_name),
) -> UUID:
    token = session or request.cookies.get(settings.session_cookie_name)
    if not token:
        raise UnauthorizedError()
    return auth.decode_token(token)


def get_current_user(
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    auth: AuthSvc,
) -> User:
    user = auth.get_user(user_id)
    if not user:
        raise UnauthorizedError()
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
