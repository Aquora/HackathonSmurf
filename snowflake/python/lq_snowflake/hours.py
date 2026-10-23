"""Expand weekly local opening hours into absolute intervals for a planning window."""

from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo


def expand_intervals(weekly, tz_name, window_start, window_end):
    """Return merged ``(opens_at, closes_at)`` aware datetimes overlapping the window.

    ``weekly`` holds slots shaped like ``osm_hours.parse`` output. Intervals are
    returned unclipped so callers see the real opening and closing times. The
    previous local day is included so overnight spans reaching into the window count.

    Arithmetic and comparisons happen in UTC: Python compares and subtracts
    datetimes that share a ZoneInfo by wall clock, which is wrong across DST.
    """
    tz = ZoneInfo(tz_name)
    day = window_start.astimezone(tz).date() - timedelta(days=1)
    last_day = window_end.astimezone(tz).date()

    raw = []
    while day <= last_day:
        for slot in weekly:
            if slot["day_of_week"] == day.weekday():
                raw.append((_utc(day, slot["open_minute"], tz), _utc(day, slot["close_minute"], tz)))
        day += timedelta(days=1)

    merged = []
    for opens_at, closes_at in sorted(raw):
        if merged and opens_at <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], closes_at))
        else:
            merged.append((opens_at, closes_at))
    return [(o.astimezone(tz), c.astimezone(tz))
            for o, c in merged if o < window_end and c > window_start]


def longest_open_seconds(intervals, window_start, window_end):
    """Longest continuous open time inside the window, in whole seconds."""
    best = 0
    start = window_start.astimezone(timezone.utc)
    end = window_end.astimezone(timezone.utc)
    for opens_at, closes_at in intervals:
        overlap = (min(closes_at.astimezone(timezone.utc), end)
                   - max(opens_at.astimezone(timezone.utc), start)).total_seconds()
        best = max(best, int(overlap))
    return best


def _utc(day, minute, tz):
    # Wall-clock time in the place's timezone; ZoneInfo resolves the DST offset.
    local = (datetime.combine(day, time()) + timedelta(minutes=minute)).replace(tzinfo=tz)
    return local.astimezone(timezone.utc)
