"""Synthetic analytics fixtures for local demo mode.

Dates are relative to "now" so demo charts always end today.
"""

from datetime import UTC, datetime, timedelta
from uuid import UUID

from config.settings import settings

DEMO_SITE_ID = UUID("00000000-0000-4000-8000-000000000001")
DEMO_SITE_DOCS_ID = UUID("00000000-0000-4000-8000-000000000002")

# Oldest → newest daily metrics (dates applied relative to today).
_CHART_METRICS = [
    {"pageviews": 18, "clicks": 3, "hovers": 12, "visitors": 14},
    {"pageviews": 22, "clicks": 5, "hovers": 15, "visitors": 16},
    {"pageviews": 15, "clicks": 2, "hovers": 9, "visitors": 12},
    {"pageviews": 28, "clicks": 7, "hovers": 22, "visitors": 21},
    {"pageviews": 31, "clicks": 6, "hovers": 19, "visitors": 23},
    {"pageviews": 24, "clicks": 4, "hovers": 14, "visitors": 18},
    {"pageviews": 35, "clicks": 9, "hovers": 28, "visitors": 27},
    {"pageviews": 29, "clicks": 5, "hovers": 17, "visitors": 22},
    {"pageviews": 21, "clicks": 3, "hovers": 11, "visitors": 17},
    {"pageviews": 42, "clicks": 11, "hovers": 34, "visitors": 31},
    {"pageviews": 38, "clicks": 8, "hovers": 26, "visitors": 28},
    {"pageviews": 33, "clicks": 6, "hovers": 21, "visitors": 25},
    {"pageviews": 27, "clicks": 4, "hovers": 16, "visitors": 20},
    {"pageviews": 19, "clicks": 5, "hovers": 13, "visitors": 15},
]

_VISITOR_POOL = [f"demo_v_{i:04d}" for i in range(240)]

# Event templates: offset from now (positive = in the past).
_EVENT_TEMPLATES = [
    {
        "id": "00000000-0000-4000-8000-000000000101",
        "ago": timedelta(minutes=18),
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
        "ago": timedelta(minutes=17),
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
        "ago": timedelta(minutes=19),
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
        "ago": timedelta(hours=1, minutes=40),
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
        "ago": timedelta(hours=2, minutes=55),
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
        "ago": timedelta(hours=3, minutes=27),
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
        "ago": timedelta(hours=4, minutes=42),
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
        "ago": timedelta(hours=6, minutes=16),
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
        "ago": timedelta(hours=8, minutes=2),
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
        "ago": timedelta(hours=9, minutes=30),
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
        "ago": timedelta(days=1, hours=2),
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
        "ago": timedelta(days=1, hours=4),
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


def _metrics_for_index(index: int) -> dict:
    """Deterministic daily metrics for any day index (oldest → newest)."""
    base = _CHART_METRICS[index % len(_CHART_METRICS)]
    # Gentle wave so longer ranges don't look like a flat repeat.
    wave = ((index * 5) % 13) - 6
    weekendish = 1 if (index % 7) in {5, 6} else 0
    pageviews = max(1, base["pageviews"] + wave - weekendish * 4)
    clicks = max(0, base["clicks"] + (wave // 3) - weekendish)
    hovers = max(0, base["hovers"] + wave - weekendish * 2)
    visitors = max(1, base["visitors"] + (wave // 2) - weekendish * 2)
    return {
        "pageviews": pageviews,
        "clicks": clicks,
        "hovers": hovers,
        "visitors": visitors,
    }


def chart_series(*, days: int = 14, tz_name: str | None = None) -> list[dict]:
    from services.stats import resolve_tz

    n = max(1, days)
    today = datetime.now(resolve_tz(tz_name)).date()
    return [
        {
            "date": (today - timedelta(days=n - 1 - index)).isoformat(),
            **_metrics_for_index(index),
        }
        for index in range(n)
    ]


def daily_visitor_sets(series: list[dict]) -> dict[str, set[str]]:
    sets: dict[str, set[str]] = {}
    previous: set[str] = set()
    for index, row in enumerate(series):
        daily = _visitor_set(
            count=int(row["visitors"]),
            day_index=index,
            previous=previous,
        )
        sets[row["date"]] = daily
        previous = daily
    return sets


# Back-compat aliases for tests that still import these names.
def __getattr__(name: str):
    if name == "_CHART_SERIES":
        return chart_series(days=14)
    if name == "_DAILY_VISITOR_SETS":
        return daily_visitor_sets(chart_series(days=14))
    if name == "_EVENTS":
        return _events_now()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def _union_visitor_count(sets: list[set[str]]) -> int:
    union: set[str] = set()
    for visitor_ids in sets:
        union |= visitor_ids
    return len(union)


def _events_now() -> list[dict]:
    now = datetime.now(UTC)
    rows = []
    for template in _EVENT_TEMPLATES:
        event = {k: v for k, v in template.items() if k != "ago"}
        event["occurred_at"] = (now - template["ago"]).strftime("%Y-%m-%dT%H:%M:%SZ")
        event.setdefault("site_id", DEMO_SITE_ID)
        event.setdefault("title", "")
        rows.append(event)
    return rows


def list_sites() -> list[dict]:
    base = settings.public_base_url.rstrip("/")
    created = datetime.now(UTC) - timedelta(days=40)
    return [
        {
            "id": str(DEMO_SITE_ID),
            "name": "demo.example.com",
            "site_key": "sk_demo_main",
            "allowed_domains": ["demo.example.com"],
            "active": True,
            "created_at": created.isoformat(),
            "snippet": f'<script defer src="{base}/dsa.js" data-site="sk_demo_main"></script>',
        },
        {
            "id": str(DEMO_SITE_DOCS_ID),
            "name": "docs.example.com",
            "site_key": "sk_demo_docs",
            "allowed_domains": ["docs.example.com"],
            "active": True,
            "created_at": (created + timedelta(days=14)).isoformat(),
            "snippet": f'<script defer src="{base}/dsa.js" data-site="sk_demo_docs"></script>',
        },
    ]


def _period_visitors_from_series(series: list[dict], visitor_sets: list[set[str]]) -> int:
    return _union_visitor_count(visitor_sets)


def visits_stats(*, days: int = 14, hours: int | None = None, tz_name: str | None = None) -> dict:
    if hours:
        return _visits_stats_hours(hours=hours, tz_name=tz_name)
    rows = chart_series(days=days, tz_name=tz_name)
    visitor_map = daily_visitor_sets(rows)
    series = []
    visitor_sets = []
    for row in rows:
        visitors = visitor_map[row["date"]]
        visitor_sets.append(visitors)
        series.append({**row, "visitors": len(visitors)})
    totals = {
        "pageviews": sum(row["pageviews"] for row in series),
        "clicks": sum(row["clicks"] for row in series),
        "hovers": sum(row["hovers"] for row in series),
        "visitors": _period_visitors_from_series(series, visitor_sets),
    }
    return {"series": series, "totals": totals}


def _visits_stats_hours(*, hours: int = 24, tz_name: str | None = None) -> dict:
    from services.stats import resolve_tz

    tz = resolve_tz(tz_name)
    end = datetime.now(UTC)
    start = end - timedelta(hours=max(1, hours))
    start_local = start.astimezone(tz)
    end_local = end.astimezone(tz)
    cursor = start_local.replace(minute=0, second=0, microsecond=0)

    day_totals = _CHART_METRICS[-1]
    per_hour = {
        "pageviews": max(1, round(day_totals["pageviews"] / 24)),
        "clicks": max(0, round(day_totals["clicks"] / 24)),
        "hovers": max(0, round(day_totals["hovers"] / 24)),
        "visitors": max(2, round(day_totals["visitors"] / 6)),
    }
    series = []
    visitor_sets = []
    previous: set[str] = set()
    offset = 0
    while cursor <= end_local:
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
                "date": cursor.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "pageviews": max(0, per_hour["pageviews"] + wobble),
                "clicks": max(0, per_hour["clicks"] + (1 if offset % 3 == 0 else 0)),
                "hovers": max(0, per_hour["hovers"] + (1 if offset % 4 == 0 else 0)),
                "visitors": len(hour_visitors),
            }
        )
        cursor += timedelta(hours=1)
        offset += 1
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
    rows = [dict(event) for event in _events_now() if UUID(str(event["site_id"])) == site_id]

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
