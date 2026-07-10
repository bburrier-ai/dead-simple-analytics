from fastapi import APIRouter, Form, Request, Response
from fastapi.responses import RedirectResponse

from core.csrf import validate_csrf
from core.exceptions import ForbiddenError
from demo import mode as demo_mode

router = APIRouter(tags=["demo"])


@router.get("/api/demo-mode")
def get_demo_mode(request: Request) -> dict:
    return {
        "available": demo_mode.available(),
        "enabled": demo_mode.enabled_from_request(request),
    }


@router.post("/demo-mode")
def set_demo_mode(
    request: Request,
    enabled: str = Form(...),
    redirect: str = Form("/"),
    csrf_token: str = Form(...),
) -> Response:
    validate_csrf(request, form_token=csrf_token)
    if not demo_mode.available():
        raise ForbiddenError("Demo mode is not available in this environment")
    target = redirect if redirect.startswith("/") else "/"
    response = RedirectResponse(url=target, status_code=303)
    demo_mode.set_mode_cookie(response, enabled.strip() == demo_mode.COOKIE_ENABLED)
    return response
