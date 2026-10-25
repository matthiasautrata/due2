"""Whether the lexical form of an XSD temporal literal names a value.

A pattern checks only a literal's shape, so `2026-02-30T12:00:00Z` and `P1W` pass one. These
functions apply the lexical rules of XSD 1.1 Part 2 §3.3.6 (`duration`), §3.3.7 (`dateTime`),
and §3.3.9 (`date`): the year has four digits, or more without a leading zero; the month is
1 to 12, and the day exists in that month of that year (proleptic Gregorian, where year 0 is a
leap year); hour 24 is valid only as `24:00:00`, with an optional all-zero fraction; a timezone
offset is at most 14 hours; and a duration has only year, month, day, hour, minute, and second
parts, at least one of them, with a `T` only before a time part. Seconds in a duration may be
written `5`, `5.`, `5.5`, or `.5` (`duSecondFrag`).

A timezone is optional in XSD. Whether one is required is decisions/0024's rule, which the
callers apply with `TIMEZONE`, or `instant_ok` for an input instant.

`tools/check_corpus.py` (policy literals, deadlines, and case instants) and `vectors.py`
(vector instants) both call these functions, so the two checkers cannot disagree on a value.
"""

from __future__ import annotations

import re

_DATE = r"(-?(?:[1-9]\d{3,}|0\d{3}))-(\d{2})-(\d{2})"
_TZ = r"(?:Z|[+-](\d{2}):(\d{2}))?"
DATETIME = re.compile(rf"^{_DATE}T(\d{{2}}):(\d{{2}}):(\d{{2}})(?:\.(\d+))?{_TZ}$")
DATE = re.compile(rf"^{_DATE}{_TZ}$")
DURATION = re.compile(
    r"^-?P(?:(\d+)Y)?(?:(\d+)M)?(?:(\d+)D)?"
    r"(T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+(?:\.\d*)?|\.\d+)S)?)?$"
)
# Anchored only at the end, for `.search`: whether a lexical form carries a timezone.
TIMEZONE = re.compile(r"(Z|[+-]\d{2}:\d{2})$")


def _day_ok(year: str, month: str, day: str) -> bool:
    """Whether the date's digits, as matched (`year` may start with `-`), name a day."""
    y, m, d = int(year), int(month), int(day)
    leap = y % 4 == 0 and (y % 100 != 0 or y % 400 == 0)
    days = [31, 29 if leap else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    return 1 <= m <= 12 and 1 <= d <= days[m - 1]


def _offset_ok(hours: str | None, minutes: str | None) -> bool:
    """Whether an offset's digits, as matched, are at most 14 hours; True when the form has no
    offset or `Z`, which leave both `None`."""
    if hours is None or minutes is None:
        return True
    oh, om = int(hours), int(minutes)
    return om <= 59 and (oh < 14 or (oh == 14 and om == 0))


def datetime_ok(lexical: str) -> bool:
    """Whether `lexical` names an `xsd:dateTime` value, with or without a timezone."""
    m = DATETIME.match(lexical)
    if not m:
        return False
    year, month, day, hour, minute, second, fraction, oh, om = m.groups()
    h, mi, s = int(hour), int(minute), int(second)
    if h == 24:
        time_ok = mi == 0 and s == 0 and int(fraction or 0) == 0
    else:
        time_ok = h <= 23 and mi <= 59 and s <= 59
    return _day_ok(year, month, day) and time_ok and _offset_ok(oh, om)


def instant_ok(lexical: str) -> bool:
    """Whether `lexical` is an input instant: an `xsd:dateTime` with a timezone
    (decisions/0024)."""
    return datetime_ok(lexical) and TIMEZONE.search(lexical) is not None


def date_ok(lexical: str) -> bool:
    """Whether `lexical` names an `xsd:date` value, with or without a timezone."""
    m = DATE.match(lexical)
    return m is not None and _day_ok(*m.groups()[:3]) and _offset_ok(*m.groups()[3:])


def duration_kinds(lexical: str) -> frozenset[str] | None:
    """The kinds of the parts `lexical` writes, `year-month` and `day-time`, or `None` when
    it names no `xsd:duration` value. A form such as `P1Y2D` returns both kinds."""
    m = DURATION.match(lexical)
    if not m:
        return None
    years, months, days, time, hours, minutes, seconds = m.groups()
    if time is not None and not (hours or minutes or seconds):
        return None  # a T with no time part after it
    kinds = {"year-month"} if years or months else set[str]()
    if days or hours or minutes or seconds:
        kinds.add("day-time")
    return frozenset(kinds) or None  # P alone has no part
