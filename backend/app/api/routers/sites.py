from uuid import UUID

from fastapi import APIRouter

from app.api.schemas import SiteCreate, SiteUpdate
from app.dependencies import CurrentUser, DemoMode, SitesSvc
from core.exceptions import AppError, NotFoundError
from core.serialize import serialize_row
from demo import fixtures as demo_fixtures

router = APIRouter(prefix="/sites", tags=["sites"])


@router.get("")
def list_sites(user: CurrentUser, service: SitesSvc, demo_mode: DemoMode) -> dict:
    _ = user
    if demo_mode:
        return {"items": demo_fixtures.list_sites()}
    sites = service.list_sites(user.id)
    return {"items": [serialize_row(s.model_dump()) for s in sites]}


@router.post("")
def create_site(
    body: SiteCreate, user: CurrentUser, service: SitesSvc, demo_mode: DemoMode
) -> dict:
    if demo_mode:
        raise AppError("Turn off demo mode to manage sites", status_code=403)
    site = service.create_site(user.id, body.name, body.allowed_domains)
    return serialize_row(site.model_dump())


@router.patch("/{site_id}")
def update_site(
    site_id: UUID,
    body: SiteUpdate,
    user: CurrentUser,
    service: SitesSvc,
    demo_mode: DemoMode,
) -> dict:
    if demo_mode:
        raise AppError("Turn off demo mode to manage sites", status_code=403)
    site = service.update_site(
        user.id,
        site_id,
        body.name,
        body.allowed_domains,
        body.site_key,
    )
    return serialize_row(site.model_dump())


@router.get("/{site_id}")
def get_site(
    site_id: UUID, user: CurrentUser, service: SitesSvc, demo_mode: DemoMode
) -> dict:
    if demo_mode:
        for site in demo_fixtures.list_sites():
            if site["id"] == str(site_id):
                return site
        raise NotFoundError("Site not found")
    return serialize_row(service.get_site(user.id, site_id).model_dump())
