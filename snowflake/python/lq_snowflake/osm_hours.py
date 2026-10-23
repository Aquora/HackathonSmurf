"""Parse a conservative subset of OpenStreetMap ``opening_hours`` syntax.

``parse`` returns:

* a list of weekly slots ``{"day_of_week", "open_minute", "close_minute"}``
  (Monday = 0; ``close_minute`` may exceed 1440 for spans past midnight),
* ``[]`` when the schedule is closed every day, or
* ``None`` when the text uses syntax outside the supported subset.

``None`` means *unknown hours*, which excludes the place from retrieval. The
parser never guesses: public-holiday rules, sunrise/sunset, month/week
selectors, comments, open-ended times, and malformed text all return ``None``.

Supported: ``24/7``; day lists and ranges (``Mo-Fr``, ``Mo,We``, ``Fr-Mo``);
one or more time ranges (``08:00-12:00,13:00-17:00``); ``off``/``closed``;
overnight spans (``18:00-02:00`` or ``18:00-26:00``); rules separated by ``;``
(later rules replace earlier ones for their days) and additional rules separated
by ``, <day>`` (which add to the preceding rule).
"""

import re

DAYS = ("Mo", "Tu", "We", "Th", "Fr", "Sa", "Su")
MINUTES_PER_DAY = 1440

_DAY = r"(?:Mo|Tu|We|Th|Fr|Sa|Su)"
_DAY_RANGE = rf"{_DAY}(?:-{_DAY})?"
_DAY_SPEC = rf"{_DAY_RANGE}(?:,{_DAY_RANGE})*"
_TIME = r"\d{1,2}:\d{2}"
_TIME_RANGE = rf"{_TIME}-{_TIME}"
_TIME_SPEC = rf"{_TIME_RANGE}(?:,{_TIME_RANGE})*"
_RULE = re.compile(
    rf"^(?:(?P<days>{_DAY_SPEC})\s+)?(?:(?P<times>{_TIME_SPEC})|(?P<off>off|closed))$"
)
_ADDITIONAL_SPLIT = re.compile(rf",\s*(?={_DAY}\b)")
_COMMA_SPACE = re.compile(r"\s*,\s*")
_OFF_WORD = re.compile(r"\b(?:off|closed)\b", re.IGNORECASE)


class _Unsupported(Exception):
    pass


def parse(text):
    if text is None:
        return None
    text = text.strip()
    if not text:
        return None
    try:
        schedule = {day: [] for day in range(7)}
        for rule in (_normalize(r) for r in text.split(";")):
            if not rule:
                continue
            _apply_rule_group(schedule, rule)
    except _Unsupported:
        return None
    return [
        {"day_of_week": day, "open_minute": o, "close_minute": c}
        for day in range(7)
        for o, c in sorted(set(schedule[day]))
    ]


def udf_parse(text):
    """Snowflake UDF handler: VARCHAR -> ARRAY (NULL when unknown)."""
    return parse(text)


def _normalize(rule):
    # Common real-world spacing/case variants: "Mo, We 09:00-12:00, 13:00-17:00", "Su Closed".
    rule = _COMMA_SPACE.sub(",", rule.strip())
    return _OFF_WORD.sub(lambda m: m.group(0).lower(), rule)


def _apply_rule_group(schedule, rule):
    if rule == "24/7":
        for day in range(7):
            schedule[day] = [(0, MINUTES_PER_DAY)]
        return
    parsed = _parse_rule(rule)
    if parsed is not None:
        days, slots = parsed
        for day in days:
            schedule[day] = list(slots)
        return
    # "Mo 08:00-12:00, Tu 09:00-12:00": the first part replaces, the rest add.
    parts = _ADDITIONAL_SPLIT.split(rule)
    if len(parts) < 2:
        raise _Unsupported(rule)
    for index, part in enumerate(parts):
        parsed = _parse_rule(part.strip())
        if parsed is None:
            raise _Unsupported(part)
        days, slots = parsed
        for day in days:
            if index == 0 or not slots:
                schedule[day] = list(slots)
            else:
                schedule[day].extend(slots)


def _parse_rule(rule):
    match = _RULE.match(rule)
    if not match:
        return None
    days = _parse_days(match.group("days")) if match.group("days") else list(range(7))
    if match.group("off"):
        return days, []
    return days, [_parse_range(r) for r in match.group("times").split(",")]


def _parse_days(spec):
    days = []
    for part in spec.split(","):
        if "-" in part:
            start, end = (DAYS.index(d) for d in part.split("-"))
            day = start
            while True:
                days.append(day)
                if day == end:
                    break
                day = (day + 1) % 7
        else:
            days.append(DAYS.index(part))
    return sorted(set(days))


def _parse_range(text):
    open_text, close_text = text.split("-")
    open_minute = _minutes(open_text)
    close_minute = _minutes(close_text)
    if open_minute >= MINUTES_PER_DAY:
        raise _Unsupported(text)
    if close_minute <= open_minute:
        if close_minute == open_minute or close_minute > MINUTES_PER_DAY:
            raise _Unsupported(text)
        close_minute += MINUTES_PER_DAY
    if close_minute - open_minute > MINUTES_PER_DAY:
        raise _Unsupported(text)
    return open_minute, close_minute


def _minutes(text):
    hours, minutes = (int(x) for x in text.split(":"))
    if minutes > 59 or hours > 48:
        raise _Unsupported(text)
    total = hours * 60 + minutes
    if total > 2 * MINUTES_PER_DAY:
        raise _Unsupported(text)
    return total
