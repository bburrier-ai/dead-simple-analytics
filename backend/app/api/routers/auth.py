from fastapi import APIRouter, Cookie, Request, Response

from app.api.schemas import LoginRequest, UserResponse
from app.dependencies import CurrentUser, DbConn
from config.settings import settings
from core.csrf import generate_csrf_token, set_csrf_cookie, validate_csrf
from core.exceptions import RateLimitError, UnauthorizedError
from core.rate_limit import SlidingWindowRateLimiter
from db.repositories.users import UsersRepository
from services.auth import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])
auth = AuthService()
_login_limiter = SlidingWindowRateLimiter()


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _check_login_rate_limit(request: Request) -> None:
    key = f"login:{_client_ip(request)}"
    if not _login_limiter.allow(
        key,
        limit=settings.login_rate_limit_attempts,
        window_sec=float(settings.login_rate_limit_window_sec),
    ):
        raise RateLimitError("Too many login attempts")


@router.get("/csrf")
def csrf(response: Response) -> dict:
    token = generate_csrf_token()
    set_csrf_cookie(response, token)
    return {"csrf_token": token}


@router.post("/login")
def login(body: LoginRequest, request: Request, response: Response, conn: DbConn) -> dict:
    validate_csrf(request)
    _check_login_rate_limit(request)
    user = UsersRepository().get_by_username(conn, body.username)
    if not user or not auth.verify_password(body.password, user["password_hash"]):
        raise UnauthorizedError("Invalid username or password")
    token = auth.create_token(user["id"])
    response.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite=settings.session_cookie_samesite,
        max_age=settings.jwt_expire_minutes * 60,
        path="/",
    )
    csrf_token = generate_csrf_token()
    set_csrf_cookie(response, csrf_token)
    return {
        "user": UserResponse(id=str(user["id"]), username=user["username"]).model_dump(),
        "csrf_token": csrf_token,
    }


@router.post("/logout")
def logout(request: Request, response: Response) -> dict:
    validate_csrf(request)
    response.delete_cookie(
        key=settings.session_cookie_name,
        path="/",
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite=settings.session_cookie_samesite,
    )
    csrf_token = generate_csrf_token()
    set_csrf_cookie(response, csrf_token)
    return {"ok": True}


@router.get("/me")
def me(user: CurrentUser) -> dict:
    return {"id": str(user["id"]), "username": user["username"]}


@router.get("/session")
def session(
    request: Request,
    conn: DbConn,
    session: str | None = Cookie(default=None, alias=settings.session_cookie_name),
) -> dict:
    token = session or request.cookies.get(settings.session_cookie_name)
    if not token:
        return {"user": None}
    user_id = auth.decode_token_optional(token)
    if not user_id:
        return {"user": None}
    user = UsersRepository().get_by_id(conn, user_id)
    if not user:
        return {"user": None}
    return {
        "user": UserResponse(id=str(user["id"]), username=user["username"]).model_dump()
    }
