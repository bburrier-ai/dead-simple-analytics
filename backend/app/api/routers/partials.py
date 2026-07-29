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

EVENT_COLUMN_LABELS = {
    "occurred_at": "Time",
    "type": "Type",
    "path": "Path",
    "track_id": "Track ID",
    "session_id": "Session",
    "visitor_hash": "Visitor",
    "visitor_id": "Visitor ID",
    "referrer": "Referrer",
    "location": "Location",
}

DEFAULT_EVENT_COLUMNS = [
    "occurred_at",
    "type",
    "path",
    "track_id",
    "session_id",
    "visitor_hash",
    "referrer",
    "location",
]

EVENTS_TABLE_LIMIT = 25


def _events_table_headers(*, total: int, page: int, limit: int) -> dict[str, str]:
    return {
        "X-Events-Total": str(total),
        "X-Events-Page": str(page),
        "X-Events-Limit": str(limit),
    }


def parse_event_columns(raw: str | None) -> list[str]:
    if not raw:
        return list(DEFAULT_EVENT_COLUMNS)
    cols: list[str] = []
    for part in raw.split(","):
        key = part.strip()
        if key in EVENT_COLUMN_LABELS and key not in cols:
            cols.append(key)
    return cols or list(DEFAULT_EVENT_COLUMNS)


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


def _shorten(value: str, limit: int = 12) -> str:
    if len(value) <= limit:
        return esc(value)
    return esc(value[:limit] + "…")


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


def _event_row_cells(e: dict) -> dict[str, str]:
    track_raw = (e.get("track_id") or "").strip()
    referrer_raw = e.get("referrer") or ""
    session_raw = e.get("session_id") or ""
    visitor_hash_raw = (e.get("visitor_hash") or "").strip()
    visitor_id_raw = (e.get("visitor_id") or "").strip()
    path_raw = e.get("path") or ""
    occurred = e.get("occurred_at") or ""
    event_type = e["type"]
    event_label = esc(_EVENT_TYPE_LABELS.get(event_type, event_type))
    ref_display = (
        esc(referrer_raw) if len(referrer_raw) <= 28 else esc(referrer_raw[:28] + "…")
    )
    location_filter = _location_filter_value(e)
    return {
        "occurred_at": _cell(
            field="occurred_at",
            value=str(occurred),
            display=_format_time(str(occurred)),
            filter_by=None,
            classes="mono",
        ),
        "type": _cell(
            field="type",
            value=event_type,
            display=(
                f'<span class="badge badge-{esc(event_type)}">{event_label}</span>'
            ),
            filter_by="type",
        ),
        "path": _cell(
            field="path",
            value=path_raw,
            display=esc(path_raw),
            filter_by="q" if path_raw else None,
            classes="mono",
        ),
        "track_id": _cell(
            field="track_id",
            value=track_raw,
            display=esc(track_raw or "-"),
            filter_by="q" if track_raw else None,
            classes="mono text-muted",
        ),
        "session_id": _cell(
            field="session_id",
            value=session_raw,
            display=_shorten(session_raw) if session_raw else "-",
            filter_by="q" if session_raw else None,
            classes="mono text-muted",
            title=session_raw or None,
        ),
        "visitor_hash": _cell(
            field="visitor_hash",
            value=visitor_hash_raw,
            display=_shorten(visitor_hash_raw) if visitor_hash_raw else "-",
            filter_by="q" if visitor_hash_raw else None,
            classes="mono text-muted",
            title=visitor_hash_raw or None,
        ),
        "visitor_id": _cell(
            field="visitor_id",
            value=visitor_id_raw,
            display=_shorten(visitor_id_raw) if visitor_id_raw else "-",
            filter_by="q" if visitor_id_raw else None,
            classes="mono text-muted",
            title=visitor_id_raw or None,
        ),
        "referrer": _cell(
            field="referrer",
            value=referrer_raw,
            display=ref_display or "-",
            filter_by="q" if referrer_raw else None,
            classes="text-muted",
            title=referrer_raw or None,
        ),
        "location": _cell(
            field="location",
            value=location_filter,
            display=_format_location(e),
            filter_by="q" if location_filter else None,
        ),
    }


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
    days: int | None = Query(None, ge=1, le=365),
    hours: int | None = Query(None, ge=1, le=168),
    tz: str | None = Query(None, max_length=64),
    columns: str | None = Query(None),
) -> HTMLResponse:
    _ = user
    col_ids = parse_event_columns(columns)
    limit = EVENTS_TABLE_LIMIT
    if demo_mode:
        data = demo_fixtures.list_events(
            site_id,
            event_type=type,
            q=q,
            sort=sort,
            order=order,
            page=page,
            limit=limit,
            days=days,
            hours=hours,
            tz_name=tz,
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
            limit=limit,
            days=days,
            hours=hours,
            tz_name=tz,
        )
    rows = data["items"]
    headers = _events_table_headers(
        total=int(data["total"]),
        page=int(data["page"]),
        limit=int(data["limit"]),
    )
    if not rows:
        return HTMLResponse(
            content=(
                f'<tr><td colspan="{len(col_ids)}" class="text-muted">'
                "No events match your filters</td></tr>"
            ),
            headers=headers,
        )

    out = []
    for e in rows:
        cells = _event_row_cells(e)
        out.append("<tr>" + "".join(cells[c] for c in col_ids if c in cells) + "</tr>")
    return HTMLResponse(content="\n".join(out), headers=headers)


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
