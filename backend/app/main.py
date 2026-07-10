import json
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from app.api.routers import auth, collect, demo_mode, events, health, pages, partials, sites, stats
from config.logging import setup_logging
from config.settings import settings
from core.csrf import validate_csrf
from core.exceptions import AppError, ForbiddenError, UnauthorizedError
from db.migrations import run_migrations
from web.paths import STATIC_DIR

logger = logging.getLogger(__name__)
COMPONENTS_DIR = Path("/components/public")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    setup_logging()
    run_migrations()
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="Dead Simple Analytics",
        description="Self-hosted analytics API and dashboard.",
        version="0.1.0",
        lifespan=lifespan,
    )
    origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins or ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(AppError)
    async def app_error_handler(_request: Request, exc: AppError):
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})

    @app.exception_handler(UnauthorizedError)
    async def unauthorized_handler(_request: Request, exc: UnauthorizedError):
        return JSONResponse(status_code=401, content={"detail": exc.message})

    @app.middleware("http")
    async def csrf_guard(request: Request, call_next):
        if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
            path = request.url.path
            if path.startswith("/api/") and path not in {"/api/auth/csrf", "/api/auth/login"}:
                try:
                    validate_csrf(request)
                except ForbiddenError as exc:
                    return JSONResponse(status_code=403, content={"detail": exc.message})
        return await call_next(request)

    @app.middleware("http")
    async def collect_cors(request: Request, call_next):
        response = await call_next(request)
        if request.url.path == "/collect":
            response.headers["Access-Control-Allow-Origin"] = "*"
            response.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type"
        return response

    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    if COMPONENTS_DIR.is_dir():
        app.mount("/components", StaticFiles(directory=COMPONENTS_DIR), name="components")

    @app.get("/components-config.js")
    def components_config() -> Response:
        url = settings.components_cdn_url.strip() or "/components"
        body = f"window.__COMPONENTS_CDN__=window.__COMPONENTS_CDN__||{json.dumps(url)};"
        return Response(content=body, media_type="application/javascript")

    @app.get("/dsa.js")
    def dsa_js() -> FileResponse:
        return FileResponse(
            STATIC_DIR / "js" / "dsa.js",
            media_type="application/javascript",
            headers={"Cache-Control": "public, max-age=3600"},
        )

    prefix = "/api"
    app.include_router(health.router, prefix=prefix)
    app.include_router(auth.router, prefix=prefix)
    app.include_router(sites.router, prefix=prefix)
    app.include_router(stats.router, prefix=prefix)
    app.include_router(events.router, prefix=prefix)
    app.include_router(collect.router)
    app.include_router(demo_mode.router)
    app.include_router(partials.router)
    app.include_router(pages.router)
    return app


app = create_app()
