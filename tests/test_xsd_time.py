"""The value checks on XSD temporal literals (`tools/harness/xsd_time.py`, #125).

A literal can have the shape of a dateTime, date, or duration and still name no value. The
corpus checker and the vector checker both ask `harness.xsd_time`, so these near misses pin
the one answer they share. Without them, a check that tested only the shape would accept
`2026-02-30T12:00:00Z`, `02026-01-01T00:00:00Z`, and `P1W`, and an evaluator would decline
a policy or vector the checkers passed.
"""

from __future__ import annotations

import pytest
from harness.xsd_time import date_ok, datetime_ok, duration_kinds, instant_ok

# (lexical form, names a value), each valid one beside the nearest invalid one.
DATETIMES = [
    ("2024-02-29T00:00:00Z", True),  # 2024 is a leap year
    ("2023-02-29T00:00:00Z", False),
    ("2000-02-29T00:00:00Z", True),  # divisible by 400
    ("1900-02-29T00:00:00Z", False),  # divisible by 100 only
    ("0000-02-29T00:00:00Z", True),  # year 0 is a leap year (proleptic Gregorian)
    ("-0000-01-01T00:00:00Z", True),  # XSD 1.1 maps -0000 to year 0 as well
    ("12026-01-01T00:00:00Z", True),
    ("02026-01-01T00:00:00Z", False),  # a year beyond four digits has no leading zero
    ("2026-04-30T00:00:00Z", True),
    ("2026-04-31T00:00:00Z", False),
    ("2026-12-01T00:00:00Z", True),
    ("2026-13-01T00:00:00Z", False),
    ("2026-01-01T24:00:00Z", True),  # the end of the day
    ("2026-01-01T24:00:01Z", False),
    ("2026-01-01T24:00:00.000Z", True),
    ("2026-01-01T24:00:00.5Z", False),
    ("2026-01-01T23:59:59.5Z", True),
    ("2026-01-01T23:60:00Z", False),
    ("2026-01-01T00:00:00+14:00", True),
    ("2026-01-01T00:00:00+14:01", False),
    ("2026-01-01T00:00:00", True),  # XSD allows no timezone; decisions/0024 does not
]
DATES = [
    ("2024-02-29", True),
    ("2023-02-29", False),
    ("02026-01-01", False),
    ("2026-01-01+14:00", True),
    ("2026-01-01+14:01", False),
]
DURATIONS = [
    ("P1Y", frozenset({"year-month"})),
    ("P7D", frozenset({"day-time"})),
    ("PT1.5S", frozenset({"day-time"})),
    ("PT.5S", frozenset({"day-time"})),  # duSecondFrag allows a bare fraction
    ("PT5.S", frozenset({"day-time"})),  # and a bare point
    ("P1Y2D", frozenset({"year-month", "day-time"})),
    ("P1W", None),  # ISO 8601's week form; xsd:duration has none
    ("P", None),  # no part
    ("PT", None),  # a T with no time part
    ("P1DT", None),
    ("PT1D", None),  # a T before a day part
    ("P1D2Y", None),  # parts out of order
]


@pytest.mark.parametrize(("lexical", "ok"), DATETIMES, ids=[d for d, _ in DATETIMES])
def test_datetime(lexical: str, ok: bool) -> None:
    assert datetime_ok(lexical) is ok


def test_an_instant_needs_a_timezone() -> None:
    assert instant_ok("2026-01-01T00:00:00Z")
    assert not instant_ok("2026-01-01T00:00:00")


@pytest.mark.parametrize(("lexical", "ok"), DATES, ids=[d for d, _ in DATES])
def test_date(lexical: str, ok: bool) -> None:
    assert date_ok(lexical) is ok


@pytest.mark.parametrize(("lexical", "kinds"), DURATIONS, ids=[d for d, _ in DURATIONS])
def test_duration(lexical: str, kinds: frozenset[str] | None) -> None:
    assert duration_kinds(lexical) == kinds
