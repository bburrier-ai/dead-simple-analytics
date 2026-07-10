from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Query
from fastapi.responses import HTMLResponse

from app.dependencies import CurrentUser, DbConn, DemoMode
from core.html import esc
from demo import fixtures as demo_fixtures
from services.events import EventsService
from services.sites import SitesService

router = APIRouter(prefix="/partials", tags=["partials"])
events_service = EventsService()
sites_service = SitesService()


def _format_time(iso: str) -> str:
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return dt.strftime("%b %d, %H:%M")
    except ValueError:
        return esc(iso)


def _format_location(row: dict) -> str:
    city = row.get("city")
    country = row.get("country")
    if city and country:
        return esc(f"{city}, {country}")
    return esc(country or "-")


@router.get("/events-table", response_class=HTMLResponse)
def events_table(
    user: CurrentUser,
    conn: DbConn,
    demo_mode: DemoMode,
    site_id: UUID = Query(...),
    type: str = Query("all"),
    q: str | None = Query(None),
    sort: str = Query("occurred_at"),
    order: str = Query("desc"),
    page: int = Query(1, ge=1),
) -> str:
    _ = user
    if demo_mode:
        data = demo_fixtures.list_events(
            site_id,
            event_type=type,
            q=q,
            sort=sort,
            order=order,
            page=page,
            limit=25,
        )
    else:
        data = events_service.list_events(
            conn,
            site_id,
            event_type=type,
            q=q,
            sort=sort,
            order=order,
            page=page,
            limit=25,
        )
    rows = data["items"]
    if not rows:
        return '<tr><td colspan="7" class="text-muted">No events match your filters</td></tr>'

    out = []
    for e in rows:
        track = esc(e.get("track_id") or "-")
        referrer = esc(e.get("referrer") or "")
        ref_display = referrer if len(referrer) <= 28 else referrer[:28] + "…"
        corr = esc(e.get("session_id") or "-")
        corr_display = corr if len(corr) <= 12 else corr[:12] + "…"
        out.append(
            f"""<tr>
          <td class="mono">{_format_time(e["occurred_at"])}</td>
          <td><span class="badge badge-{esc(e["type"])}">{esc(e["type"])}</span></td>
          <td class="mono">{esc(e.get("path") or "")}</td>
          <td class="mono text-muted">{track}</td>
          <td class="mono text-muted" title="{corr}">{corr_display}</td>
          <td class="text-muted" title="{referrer}">{ref_display or "-"}</td>
          <td>{_format_location(e)}</td>
        </tr>"""
        )
    return "\n".join(out)


@router.get("/sites-table", response_class=HTMLResponse)
def sites_table(user: CurrentUser, conn: DbConn, demo_mode: DemoMode) -> str:
    if demo_mode:
        sites = demo_fixtures.list_sites()
    else:
        sites = sites_service.list_sites(conn, user["id"])
    if not sites:
        return '<tr><td colspan="5" class="text-muted">No sites yet - add one below.</td></tr>'

    out = []
    for site in sites:
        site_id = str(site["id"])
        domains_list = site.get("allowed_domains") or []
        domains = ", ".join(domains_list)
        snippet = site.get("snippet") or sites_service.snippet_for(site["site_key"])
        curl = sites_service.curl_for(site["site_key"], domains_list)
        out.append(
            f"""<tr class="no-click site-row"
          data-site-id="{esc(site_id)}"
          data-site-name="{esc(site["name"])}"
          data-site-domains="{esc(domains)}"
          data-site-key="{esc(site["site_key"])}"
          data-site-snippet="{esc(snippet)}">
          <td>{esc(site["name"])}</td>
          <td class="text-muted">{esc(domains)}</td>
          <td class="mono">{esc(site["site_key"])}</td>
          <td class="site-actions">
            <button type="button" class="btn" data-copy-snippet="{esc(snippet)}">
              Copy tag
            </button>
            <button type="button" class="btn" data-curl-test="{esc(curl)}">
              Test w/curl
            </button>
          </td>
          <td><button type="button" class="btn" data-edit-site>Edit</button></td>
        </tr>"""
        )
    return "\n".join(out)
