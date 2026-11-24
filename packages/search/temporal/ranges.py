"""E005 date-range parsing, relative to a fixed reference time (no wall clock).

Supported (closed set): today, yesterday, this week, last week, this month, last month,
in <Month> [<year>], since <YYYY-MM-DD>, before <YYYY-MM-DD>, on <YYYY-MM-DD>.
Weeks start Monday. Ranges are half-open [start, end) in UTC.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping
from datetime import UTC, datetime, timedelta

MONTHS = {
    m: i
    for i, m in enumerate(
        [
            "january",
            "february",
            "march",
            "april",
            "may",
            "june",
            "july",
            "august",
            "september",
            "october",
            "november",
            "december",
        ],
        1,
    )
}
_DATE = r"(\d{4}-\d{2}-\d{2})"
PATTERNS = [
    ("today", r"\btoday\b"),
    ("yesterday", r"\byesterday\b"),
    ("this_week", r"\bthis week\b"),
    ("last_week", r"\b(?:from\s+)?last week\b"),
    ("this_month", r"\bthis month\b"),
    ("last_month", r"\b(?:from\s+)?last month\b"),
    ("in_month", r"\bin (" + "|".join(MONTHS) + r")(?:\s+(\d{4}))?\b"),
    ("since", r"\bsince " + _DATE),
    ("before", r"\bbefore " + _DATE),
    ("on", r"\bon " + _DATE),
]


def _day(d: datetime) -> datetime:
    return d.replace(hour=0, minute=0, second=0, microsecond=0)


def _month_start(y: int, m: int) -> datetime:
    return datetime(y, m, 1, tzinfo=UTC)


def _next_month(d: datetime) -> datetime:
    return _month_start(d.year + (d.month == 12), 1 if d.month == 12 else d.month + 1)


def parse_range(
    query: str, ref: datetime
) -> tuple[str, tuple[datetime, datetime] | None, str | None]:
    """Returns (query without the temporal phrase, (start, end) or None, operator)."""
    low = query.lower()
    ref = ref.astimezone(UTC)
    today = _day(ref)
    for op, pat in PATTERNS:
        m = re.search(pat, low)
        if not m:
            continue
        if op == "today":
            rng = (today, today + timedelta(days=1))
        elif op == "yesterday":
            rng = (today - timedelta(days=1), today)
        elif op == "this_week":
            s = today - timedelta(days=today.weekday())
            rng = (s, ref + timedelta(seconds=1))
        elif op == "last_week":
            s = today - timedelta(days=today.weekday() + 7)
            rng = (s, s + timedelta(days=7))
        elif op == "this_month":
            rng = (_month_start(ref.year, ref.month), ref + timedelta(seconds=1))
        elif op == "last_month":
            e = _month_start(ref.year, ref.month)
            s = _month_start(e.year - (e.month == 1), 12 if e.month == 1 else e.month - 1)
            rng = (s, e)
        elif op == "in_month":
            mon = MONTHS[m.group(1)]
            y = int(m.group(2)) if m.group(2) else (ref.year if mon <= ref.month else ref.year - 1)
            s = _month_start(y, mon)
            rng = (s, _next_month(s))
        else:
            d = datetime.fromisoformat(m.group(1)).replace(tzinfo=UTC)
            rng = {
                "since": (d, datetime.max.replace(tzinfo=UTC)),
                "before": (datetime.min.replace(tzinfo=UTC), d),
                "on": (d, d + timedelta(days=1)),
            }[op]
        stripped = re.sub(r"\s+", " ", query[: m.start()] + " " + query[m.end() :]).strip()
        return stripped, rng, op
    return query, None, None


def make_range_parser(
    timestamps: Mapping[str, datetime | None], ref: datetime
) -> Callable[[str], tuple[str, Callable[[str], bool] | None, dict[str, object]]]:
    """Adapter for FilterStage."""

    def parse(query: str) -> tuple[str, Callable[[str], bool] | None, dict[str, object]]:
        q, rng, op = parse_range(query, ref)
        if rng is None:
            return query, None, {"operator": None}
        s, e = rng

        def keep(document_id: str) -> bool:
            timestamp = timestamps.get(document_id)
            return timestamp is not None and s <= timestamp < e

        return q, keep, {"operator": op, "start": s.isoformat(), "end": e.isoformat()}

    return parse
