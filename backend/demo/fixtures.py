"""Synthetic analytics fixtures for local demo mode."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

from config.settings import settings

DEMO_SITE_ID = UUID("00000000-0000-4000-8000-000000000001")
DEMO_SITE_DOCS_ID = UUID("00000000-0000-4000-8000-000000000002")

_CHART_SERIES = [
    {"date": "2026-06-25", "pageviews": 18, "clicks": 3, "hovers": 12, "visitors": 14},
    {"date": "2026-06-26", "pageviews": 22, "clicks": 5, "hovers": 15, "visitors": 16},
    {"date": "2026-06-27", "pageviews": 15, "clicks": 2, "hovers": 9, "visitors": 12},
    {"date": "2026-06-28", "pageviews": 28, "clicks": 7, "hovers": 22, "visitors": 21},
    {"date": "2026-06-29", "pageviews": 31, "clicks": 6, "hovers": 19, "visitors": 23},
    {"date": "2026-06-30", "pageviews": 24, "clicks": 4, "hovers": 14, "visitors": 18},
    {"date": "2026-07-01", "pageviews": 35, "clicks": 9, "hovers": 28, "visitors": 27},
    {"date": "2026-07-02", "pageviews": 29, "clicks": 5, "hovers": 17, "visitors": 22},
    {"date": "2026-07-03", "pageviews": 21, "clicks": 3, "hovers": 11, "visitors": 17},
    {"date": "2026-07-04", "pageviews": 42, "clicks": 11, "hovers": 34, "visitors": 31},
    {"date": "2026-07-05", "pageviews": 38, "clicks": 8, "hovers": 26, "visitors": 28},
    {"date": "2026-07-06", "pageviews": 33, "clicks": 6, "hovers": 21, "visitors": 25},
    {"date": "2026-07-07", "pageviews": 27, "clicks": 4, "hovers": 16, "visitors": 20},
    {"date": "2026-07-08", "pageviews": 19, "clicks": 5, "hovers": 13, "visitors": 15},
]

_VISITOR_POOL = [f"demo_v_{i:04d}" for i in range(240)]


def _visitor_set(
    *,
    count: int,
    day_index: int,
    previous: set[str],
    overlap_ratio: float = 0.45,
) -> set[str]:
    count = max(0, count)
    if count == 0:
        return set()

    overlap = min(len(previous), int(round(count * overlap_ratio)))
    retained = set(list(previous)[:overlap]) if previous else set()
    chosen = set(retained)
    cursor = (day_index * 17) % len(_VISITOR_POOL)

    while len(chosen) < count:
        visitor_id = _VISITOR_POOL[cursor % len(_VISITOR_POOL)]
        cursor += 1
        if visitor_id not in chosen:
            chosen.add(visitor_id)

    return chosen


def _build_daily_visitor_sets() -> dict[str, set[str]]:
    sets: dict[str, set[str]] = {}
    previous: set[str] = set()
    for index, row in enumerate(_CHART_SERIES):
        daily = _visitor_set(
            count=int(row["visitors"]),
            day_index=index,
            previous=previous,
        )
        sets[row["date"]] = daily
        previous = daily
    return sets


_DAILY_VISITOR_SETS = _build_daily_visitor_sets()


def _union_visitor_count(sets: list[set[str]]) -> int:
    union: set[str] = set()
    for visitor_ids in sets:
        union |= visitor_ids
    return len(union)

_EVENTS = [
    {
        "id": "00000000-0000-4000-8000-000000000101",
        "occurred_at": "2026-07-08T18:42:10Z",
        "type": "hover",
        "path": "/",
        "track_id": "cta-contact",
        "referrer": "https://google.com/",
        "country": "US",
        "city": "Portland",
        "visitor_id": "v_8f2a1c",
        "session_id": "sess_8f2a1c",
    },
    {
        "id": "00000000-0000-4000-8000-000000000102",
        "occurred_at": "2026-07-08T18:42:11Z",
        "type": "click",
        "path": "/",
        "track_id": "cta-contact",
        "referrer": "https://google.com/",
        "country": "US",
        "city": "Portland",
        "visitor_id": "v_8f2a1c",
        "session_id": "sess_8f2a1c",
    },
    {
        "id": "00000000-0000-4000-8000-000000000103",
        "occurred_at": "2026-07-08T18:41:55Z",
        "type": "pageview",
        "path": "/",
        "track_id": "",
        "referrer": "https://google.com/",
        "country": "US",
        "city": "Portland",
        "visitor_id": "v_8f2a1c",
        "session_id": "sess_8f2a1c",
    },
    {
        "id": "00000000-0000-4000-8000-000000000104",
        "occurred_at": "2026-07-08T17:20:03Z",
        "type": "pageview",
        "path": "/blog/open-source",
        "track_id": "",
        "referrer": "https://example.com/",
        "country": "DE",
        "city": "Berlin",
        "visitor_id": "v_3d91ef",
        "session_id": "sess_3d91ef",
    },
    {
        "id": "00000000-0000-4000-8000-000000000105",
        "occurred_at": "2026-07-08T16:05:44Z",
        "type": "click",
        "path": "/blog/open-source",
        "track_id": "share-twitter",
        "referrer": "",
        "country": "DE",
        "city": "Berlin",
        "visitor_id": "v_3d91ef",
        "session_id": "sess_3d91ef",
    },
    {
        "id": "00000000-0000-4000-8000-000000000106",
        "occurred_at": "2026-07-08T15:33:22Z",
        "type": "pageview",
        "path": "/",
        "track_id": "",
        "referrer": "https://github.com/",
        "country": "US",
        "city": "San Francisco",
        "visitor_id": "v_a104bc",
        "session_id": "sess_a104bc",
    },
    {
        "id": "00000000-0000-4000-8000-000000000107",
        "occurred_at": "2026-07-08T14:18:09Z",
        "type": "click",
        "path": "/",
        "track_id": "nav-projects",
        "referrer": "https://github.com/",
        "country": "US",
        "city": "San Francisco",
        "visitor_id": "v_a104bc",
        "session_id": "sess_a104bc",
    },
    {
        "id": "00000000-0000-4000-8000-000000000108",
        "occurred_at": "2026-07-08T12:44:30Z",
        "type": "pageview",
        "path": "/",
        "track_id": "",
        "referrer": "",
        "country": "CA",
        "city": "Toronto",
        "visitor_id": "v_77e2d0",
        "session_id": "sess_77e2d0",
    },
    {
        "id": "00000000-0000-4000-8000-000000000109",
        "occurred_at": "2026-07-08T10:58:07Z",
        "type": "pageview",
        "path": "/",
        "track_id": "",
        "referrer": "https://news.ycombinator.com/",
        "country": "GB",
        "city": "London",
        "visitor_id": "v_c4b892",
        "session_id": "sess_c4b892",
    },
    {
        "id": "00000000-0000-4000-8000-00000000010a",
        "occurred_at": "2026-07-08T09:30:44Z",
        "type": "pageview",
        "path": "/resume",
        "track_id": "",
        "referrer": "https://linkedin.com/",
        "country": "US",
        "city": "Austin",
        "visitor_id": "v_1f883a",
        "session_id": "sess_1f883a",
    },
    {
        "id": "00000000-0000-4000-8000-00000000010b",
        "occurred_at": "2026-07-07T20:11:02Z",
        "type": "pageview",
        "path": "/docs/getting-started",
        "track_id": "",
        "referrer": "https://example.com/",
        "country": "NL",
        "city": "Amsterdam",
        "visitor_id": "v_2b7c14",
        "session_id": "sess_2b7c14",
        "site_id": DEMO_SITE_DOCS_ID,
    },
    {
        "id": "00000000-0000-4000-8000-00000000010c",
        "occurred_at": "2026-07-07T18:33:55Z",
        "type": "click",
        "path": "/docs/getting-started",
        "track_id": "cta-github",
        "referrer": "",
        "country": "NL",
        "city": "Amsterdam",
        "visitor_id": "v_2b7c14",
        "session_id": "sess_2b7c14",
        "site_id": DEMO_SITE_DOCS_ID,
    },
]

for i, event in enumerate(_EVENTS):
    event.setdefault("site_id", DEMO_SITE_ID)
    event.setdefault("title", "")


def list_sites() -> list[dict]:
    base = settings.public_base_url.rstrip("/")
    return [
        {
            "id": str(DEMO_SITE_ID),
            "name": "demo.example.com",
            "site_key": "sk_demo_main",
            "allowed_domains": ["demo.example.com"],
            "active": True,
            "created_at": datetime(2026, 6, 1, tzinfo=UTC).isoformat(),
            "snippet": f'<script defer src="{base}/dsa.js" data-site="sk_demo_main"></script>',
        },
        {
            "id": str(DEMO_SITE_DOCS_ID),
            "name": "docs.example.com",
            "site_key": "sk_demo_docs",
            "allowed_domains": ["docs.example.com"],
            "active": True,
            "created_at": datetime(2026, 6, 15, tzinfo=UTC).isoformat(),
            "snippet": f'<script defer src="{base}/dsa.js" data-site="sk_demo_docs"></script>',
        },
    ]


def _period_visitors_from_series(series: list[dict], visitor_sets: list[set[str]]) -> int:
    return _union_visitor_count(visitor_sets)


def visits_stats(*, days: int = 14, hours: int | None = None) -> dict:
    if hours:
        return _visits_stats_hours(hours=hours)
    rows = _CHART_SERIES[-days:] if days < len(_CHART_SERIES) else list(_CHART_SERIES)
    series = []
    visitor_sets = []
    for row in rows:
        visitors = _DAILY_VISITOR_SETS[row["date"]]
        visitor_sets.append(visitors)
        series.append({**row, "visitors": len(visitors)})
    totals = {
        "pageviews": sum(row["pageviews"] for row in series),
        "clicks": sum(row["clicks"] for row in series),
        "hovers": sum(row["hovers"] for row in series),
        "visitors": _period_visitors_from_series(series, visitor_sets),
    }
    return {"series": series, "totals": totals}


def _visits_stats_hours(*, hours: int = 24) -> dict:
    now = datetime.now(UTC).replace(minute=0, second=0, microsecond=0)
    day_totals = _CHART_SERIES[-1]
    per_hour = {
        "pageviews": max(1, round(day_totals["pageviews"] / 24)),
        "clicks": max(0, round(day_totals["clicks"] / 24)),
        "hovers": max(0, round(day_totals["hovers"] / 24)),
        "visitors": max(2, round(day_totals["visitors"] / 6)),
    }
    series = []
    visitor_sets = []
    previous: set[str] = set()
    for offset in range(hours - 1, -1, -1):
        hour = now - timedelta(hours=offset)
        wobble = (offset % 5) - 2
        visitor_count = max(1, per_hour["visitors"] + (1 if offset % 6 == 0 else 0))
        hour_visitors = _visitor_set(
            count=visitor_count,
            day_index=offset,
            previous=previous,
            overlap_ratio=0.55,
        )
        previous = hour_visitors
        visitor_sets.append(hour_visitors)
        series.append(
            {
                "date": hour.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "pageviews": max(0, per_hour["pageviews"] + wobble),
                "clicks": max(0, per_hour["clicks"] + (1 if offset % 3 == 0 else 0)),
                "hovers": max(0, per_hour["hovers"] + (1 if offset % 4 == 0 else 0)),
                "visitors": len(hour_visitors),
            }
        )
    totals = {
        "pageviews": sum(row["pageviews"] for row in series),
        "clicks": sum(row["clicks"] for row in series),
        "hovers": sum(row["hovers"] for row in series),
        "visitors": _period_visitors_from_series(series, visitor_sets),
    }
    return {"series": series, "totals": totals}


def list_events(
    site_id: UUID,
    *,
    event_type: str = "all",
    q: str | None = None,
    sort: str = "occurred_at",
    order: str = "desc",
    page: int = 1,
    limit: int = 50,
) -> dict:
    rows = [dict(event) for event in _EVENTS if UUID(str(event["site_id"])) == site_id]

    if event_type and event_type != "all":
        rows = [row for row in rows if row["type"] == event_type]

    if q:
        needle = q.strip().lower()
        rows = [
            row
            for row in rows
            if needle in row["path"].lower()
            or needle in (row.get("track_id") or "").lower()
            or needle in (row.get("referrer") or "").lower()
            or needle in (row.get("visitor_id") or "").lower()
            or needle in (row.get("session_id") or "").lower()
            or needle in (row.get("city") or "").lower()
        ]

    reverse = order.lower() != "asc"

    def sort_key(row: dict):
        value = row.get(sort) or ""
        if sort == "occurred_at":
            return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return str(value).lower()

    rows.sort(key=sort_key, reverse=reverse)

    total = len(rows)
    start = max(0, (page - 1) * limit)
    page_rows = rows[start : start + limit]
    return {"items": page_rows, "total": total, "page": page, "limit": limit}
