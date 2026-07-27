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

_EVENT_TYPE_LABELS = {
    "pageview": "view",
    "click": "click",
    "hover": "hover",
    "custom": "custom",
}


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


def _location_filter_value(row: dict) -> str:
    city = (row.get("city") or "").strip()
    if city:
        return city
    return (row.get("country") or "").strip()


def _cell(
    *,
    field: str,
    value: str,
    display: str,
    filter_by: str | None,
    classes: str = "",
    title: str | None = None,
) -> str:
    class_attr = f' class="{classes}"' if classes else ""
    title_attr = f' title="{esc(title)}"' if title else ""
    filter_attr = f' data-filter="{esc(filter_by)}"' if filter_by else ""
    return (
        f"<td{class_attr}{title_attr} data-field=\"{esc(field)}\" "
        f'data-value="{esc(value)}"{filter_attr}>{display}</td>'
    )


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
        track_raw = (e.get("track_id") or "").strip()
        referrer_raw = e.get("referrer") or ""
        session_raw = e.get("session_id") or ""
        path_raw = e.get("path") or ""
        occurred = e.get("occurred_at") or ""
        event_type = e["type"]
        event_label = esc(_EVENT_TYPE_LABELS.get(event_type, event_type))
        ref_display = (
            esc(referrer_raw)
            if len(referrer_raw) <= 28
            else esc(referrer_raw[:28] + "…")
        )
        corr_display = (
            esc(session_raw)
            if len(session_raw) <= 12
            else esc(session_raw[:12] + "…")
        )
        location_filter = _location_filter_value(e)
        out.append(
            "<tr>"
            + _cell(
                field="occurred_at",
                value=str(occurred),
                display=_format_time(str(occurred)),
                filter_by=None,
                classes="mono",
            )
            + _cell(
                field="type",
                value=event_type,
                display=f'<span class="badge badge-{esc(event_type)}">{event_label}</span>',
                filter_by="type",
            )
            + _cell(
                field="path",
                value=path_raw,
                display=esc(path_raw),
                filter_by="q" if path_raw else None,
                classes="mono",
            )
            + _cell(
                field="track_id",
                value=track_raw,
                display=esc(track_raw or "-"),
                filter_by="q" if track_raw else None,
                classes="mono text-muted",
            )
            + _cell(
                field="session_id",
                value=session_raw,
                display=corr_display if session_raw else "-",
                filter_by="q" if session_raw else None,
                classes="mono text-muted",
                title=session_raw or None,
            )
            + _cell(
                field="referrer",
                value=referrer_raw,
                display=ref_display or "-",
                filter_by="q" if referrer_raw else None,
                classes="text-muted",
                title=referrer_raw or None,
            )
            + _cell(
                field="location",
                value=location_filter,
                display=_format_location(e),
                filter_by="q" if location_filter else None,
            )
            + "</tr>"
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
        name = esc(site["name"])
        key = esc(site["site_key"])
        domains_esc = esc(domains)
        snippet_esc = esc(snippet)
        curl_esc = esc(curl)
        out.append(
            f"""<tr class="no-click site-row"
          data-site-id="{esc(site_id)}"
          data-site-name="{name}"
          data-site-domains="{domains_esc}"
          data-site-key="{key}"
          data-site-snippet="{snippet_esc}">
          <td class="site-summary">
            <span class="site-summary-desktop">{name}</span>
            <ul class="site-summary-mobile">
              <li><span class="site-summary-label">Name:</span> {name}</li>
              <li><span class="site-summary-label">Domains:</span> {domains_esc}</li>
              <li>
                <span class="site-summary-label">Site key:</span>
                <span class="mono">{key}</span>
              </li>
            </ul>
          </td>
          <td class="site-col-domains text-muted">{domains_esc}</td>
          <td class="site-col-key mono">{key}</td>
          <td class="site-actions">
            <button type="button"
              class="site-menu-btn"
              data-site-menu
              aria-label="Site actions"
              aria-haspopup="menu"
              aria-expanded="false"
              data-copy-snippet="{snippet_esc}"
              data-curl-test="{curl_esc}">
              <span class="site-menu-icon" aria-hidden="true"></span>
            </button>
          </td>
          <td class="site-edit-col">
            <button type="button" class="btn" data-edit-site>Edit</button>
          </td>
        </tr>"""
        )
    return "\n".join(out)
