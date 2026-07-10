from fastapi import APIRouter
from fastapi.responses import FileResponse, RedirectResponse

from web.paths import STATIC_DIR

router = APIRouter(tags=["pages"])


@router.get("/favicon.ico", include_in_schema=False)
def favicon() -> FileResponse:
    return FileResponse(STATIC_DIR / "favicon.ico")


@router.get("/login")
def login_page() -> FileResponse:
    return FileResponse(STATIC_DIR / "login.html")


@router.get("/")
def dashboard_page() -> FileResponse:
    return FileResponse(STATIC_DIR / "dashboard.html")


@router.get("/sites")
def sites_page() -> FileResponse:
    return FileResponse(STATIC_DIR / "sites.html")


@router.get("/dashboard")
def dashboard_alias() -> RedirectResponse:
    return RedirectResponse("/", status_code=302)
