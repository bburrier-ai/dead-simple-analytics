from collections.abc import Generator
from typing import Annotated
from uuid import UUID

from fastapi import Cookie, Depends, Request
from sqlalchemy.engine import Connection

from config.settings import settings
from core.exceptions import UnauthorizedError
from db.connection import get_connection
from db.repositories.users import UsersRepository
from demo import mode as demo_mode
from services.auth import AuthService

auth_service = AuthService()


def get_db() -> Generator[Connection, None, None]:
    with get_connection() as conn:
        yield conn


DbConn = Annotated[Connection, Depends(get_db)]


def get_demo_mode(request: Request) -> bool:
    return demo_mode.enabled_from_request(request)


DemoMode = Annotated[bool, Depends(get_demo_mode)]


def get_current_user_id(
    request: Request,
    session: str | None = Cookie(default=None, alias=settings.session_cookie_name),
) -> UUID:
    token = session or request.cookies.get(settings.session_cookie_name)
    if not token:
        raise UnauthorizedError()
    return auth_service.decode_token(token)


def get_current_user(
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    conn: DbConn,
) -> dict:
    user = UsersRepository().get_by_id(conn, user_id)
    if not user:
        raise UnauthorizedError()
    return user


CurrentUser = Annotated[dict, Depends(get_current_user)]
