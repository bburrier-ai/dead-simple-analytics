from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, RedirectResponse, Response

from config.settings import settings
from services.auth import AuthService
from web.paths import STATIC_DIR

router = APIRouter(tags=["pages"])
auth_service = AuthService()


def _has_valid_session(request: Request) -> bool:
    token = request.cookies.get(settings.session_cookie_name)
    if not token:
        return False
    return auth_service.decode_token_optional(token) is not None


@router.get("/favicon.ico", include_in_schema=False)
def favicon() -> FileResponse:
    return FileResponse(STATIC_DIR / "favicon.ico")


@router.get("/login", response_model=None)
def login_page(request: Request) -> Response:
    if _has_valid_session(request):
        return RedirectResponse("/", status_code=302)
    return FileResponse(STATIC_DIR / "login.html")


@router.get("/", response_model=None)
def dashboard_page(request: Request) -> Response:
    if not _has_valid_session(request):
        return RedirectResponse("/login", status_code=302)
    return FileResponse(STATIC_DIR / "dashboard.html")


@router.get("/sites", response_model=None)
def sites_page(request: Request) -> Response:
    if not _has_valid_session(request):
        return RedirectResponse("/login", status_code=302)
    return FileResponse(STATIC_DIR / "sites.html")


@router.get("/dashboard")
def dashboard_alias() -> RedirectResponse:
    return RedirectResponse("/", status_code=302)
