from fastapi import APIRouter, Request

from core.exceptions import AppError
from db.connection import check_db_connection

router = APIRouter(tags=["health"])


@router.get("/healthz")
def healthz() -> dict:
    return {"status": "ok"}


@router.get("/readyz")
def readyz(request: Request) -> dict:
    engine = getattr(request.app.state, "db_engine", None)
    if engine is None:
        raise AppError("Database engine is not ready", status_code=503)
    check_db_connection(engine)
    return {"status": "ready"}
