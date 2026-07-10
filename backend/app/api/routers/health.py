from fastapi import APIRouter

from db.connection import check_db_connection

router = APIRouter(tags=["health"])


@router.get("/healthz")
def healthz() -> dict:
    return {"status": "ok"}


@router.get("/readyz")
def readyz() -> dict:
    check_db_connection()
    return {"status": "ready"}
