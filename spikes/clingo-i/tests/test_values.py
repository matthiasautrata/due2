"""The value table (DESIGN.md § Values): order against Python's own arithmetic, pass-through,
sums, and the placement edges."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal
from fractions import Fraction

import pytest
from clingo import Function, String, Symbol
from hypothesis import given
from hypothesis import strategies as st

from clingo_i.values import XSD, Instant, Placed, add, date_time, duration, place, value_facts

EPOCH = datetime(1970, 1, 1, tzinfo=UTC)


def lit(lex: str, local: str) -> Symbol:
    return Function("lit", [String(lex), String(XSD + local)])


def key(lex: str, local: str) -> Fraction:
    placed = place(lex, XSD + local)
    assert isinstance(placed, Placed), (lex, placed)
    return placed.key


def positions(lits: list[Symbol]) -> dict[str, int]:
    """Each placed literal's position, by lexical form."""
    return {
        f.arguments[0].arguments[0].string: f.arguments[2].number
        for f in value_facts(lits)
        if f.match("value", 3)
    }


def seconds(td: timedelta) -> Fraction:
    return Fraction(td.days * 86400 + td.seconds) + Fraction(td.microseconds, 10**6)


# --- the oracles: Decimal, datetime, and timedelta ---


@st.composite
def decimal_lex(draw: st.DrawFn) -> tuple[str, Decimal]:
    d = draw(st.decimals(allow_nan=False, allow_infinity=False, places=draw(st.integers(0, 8))))
    text = format(d, "f")
    if "." in text and draw(st.booleans()):
        text += "0" * draw(st.integers(1, 3))  # 5.0 and 5.000 are the same value
    if not text.startswith("-") and draw(st.booleans()):
        text = "+" + text
    return text, d


@given(st.lists(decimal_lex(), min_size=1, max_size=8))
def test_numeric_order(values: list[tuple[str, Decimal]]) -> None:
    lits = [lit(t, "decimal") for t, _ in values]
    pos = positions(lits)
    for t, d in values:
        assert key(t, "decimal") == Fraction(d)
        for u, e in values:
            assert (pos[t] < pos[u]) == (d < e)
            assert (pos[t] == pos[u]) == (d == e)


OFFSETS = st.integers(-14 * 60, 14 * 60).map(lambda m: timezone(timedelta(minutes=m)))


def instant_lex(dt: datetime, digits: int, zulu: bool) -> str:
    frac = f"{dt.microsecond:06d}" + "0" * max(0, digits - 6)
    frac = frac[:digits] if digits < 6 and frac[digits:].strip("0") == "" else frac
    off = dt.utcoffset()
    assert off is not None
    minutes = int(off.total_seconds()) // 60
    if minutes == 0 and zulu:
        tz = "Z"
    else:
        sign = "-" if minutes < 0 else "+"
        tz = f"{sign}{abs(minutes) // 60:02d}:{abs(minutes) % 60:02d}"
    lex = f"{dt.year:04d}-{dt.month:02d}-{dt.day:02d}T{dt.hour:02d}:{dt.minute:02d}:{dt.second:02d}"
    return lex + (f".{frac}" if frac else "") + tz


INSTANTS = st.datetimes(
    min_value=datetime(2, 1, 1), max_value=datetime(9998, 12, 31), timezones=OFFSETS
)


@given(st.lists(st.tuples(INSTANTS, st.integers(0, 9), st.booleans()), min_size=1, max_size=8))
def test_instant_order(draws: list[tuple[datetime, int, bool]]) -> None:
    lexes = [instant_lex(dt, n, z) for dt, n, z in draws]
    pos = positions([lit(x, "dateTime") for x in lexes])
    for (dt, _, _), x in zip(draws, lexes, strict=True):
        assert key(x, "dateTime") == seconds(dt - EPOCH), x
        for (et, _, _), y in zip(draws, lexes, strict=True):
            assert (pos[x] < pos[y]) == (dt < et)


@given(st.timedeltas(min_value=timedelta(days=-(10**6)), max_value=timedelta(days=10**6)))
def test_daytime_duration(td: timedelta) -> None:
    total = seconds(td)
    sign, mag = ("-" if total < 0 else ""), abs(total)
    whole, frac = divmod(mag, 1)
    days, rest = divmod(int(whole), 86400)
    hours, rest = divmod(rest, 3600)
    minutes, secs = divmod(rest, 60)
    s = f"{secs}" + (f".{int(frac * 10**6):06d}" if frac else "")
    lex = f"{sign}P{days}DT{hours}H{minutes}M{s}S"
    assert key(lex, "dayTimeDuration") == total
    assert key(lex, "duration") == total


@given(INSTANTS, st.integers(-(10**8), 10**8))
def test_daytime_sum(dt: datetime, n: int) -> None:
    i = date_time(instant_lex(dt, 6, zulu=True))
    d = duration(f"{'-' if n < 0 else ''}PT{abs(n)}S")
    assert isinstance(i, Instant) and d is not None
    assert add(i, d[0]) == seconds(dt + timedelta(seconds=n) - EPOCH)


# --- positions ---


def test_int32_passes_through() -> None:
    pos = positions([lit("-7", "integer"), lit("5", "int"), lit("5.00", "decimal")])
    assert pos == {"-7": -7, "5": 5, "5.00": 5}


@pytest.mark.parametrize(
    ("other", "expected"),
    [
        ("2147483648", {"-7": 0, "3": 1, "2147483648": 2}),  # beyond 32 bits
        ("0.5", {"-7": 0, "0.5": 1, "3": 2}),  # not an integer
    ],
)
def test_outside_int32_ranks(other: str, expected: dict[str, int]) -> None:
    assert positions([lit("-7", "integer"), lit(other, "decimal"), lit("3", "integer")]) == expected


def test_spaces_rank_apart() -> None:
    # The day 2026-01-01 and the instant at its UTC midnight share no ranking.
    pos = positions([lit("2026-01-01", "date"), lit("2026-01-01T00:00:00Z", "dateTime")])
    assert pos == {"2026-01-01": 0, "2026-01-01T00:00:00Z": 0}


# --- sums (XSD 1.1 Part 2 Appendix E) ---


@pytest.mark.parametrize(
    ("start", "dur", "end"),
    [
        ("2000-01-12T12:13:14Z", "P1Y3M5DT7H10M3.3S", "2001-04-17T19:23:17.3Z"),  # Appendix E
        ("2000-01-31T00:00:00Z", "P1M", "2000-02-29T00:00:00Z"),  # the day clamped, leap year
        ("2001-01-31T00:00:00Z", "P1M", "2001-02-28T00:00:00Z"),
        ("2000-03-31T00:00:00Z", "-P1M", "2000-02-29T00:00:00Z"),
        # Months are added in the instant's own timezone: Mar 1 local is Feb 29 in UTC.
        ("2000-03-01T05:00:00+14:00", "P1M", "2000-03-31T15:00:00Z"),
    ],
)
def test_sum(start: str, dur: str, end: str) -> None:
    i, d = date_time(start), duration(dur)
    assert isinstance(i, Instant) and d is not None
    assert add(i, d[0]) == key(end, "dateTime")


def test_mixed_durations_split() -> None:
    # P1Y3M5DT… is mixed, so it is unplaceable; its sum is still defined (Appendix E).
    assert place("P1Y3M5DT7H10M3.3S", XSD + "duration") == "value: mixed xsd:duration"


def test_plus_joins_instant_ranking() -> None:
    a, b = lit("2026-01-01T00:00:00Z", "dateTime"), lit("2026-01-02T12:00:00Z", "dateTime")
    d = lit("P1D", "dayTimeDuration")
    facts = value_facts([a, b, d])
    plus = {
        (f.arguments[0], f.arguments[1]): f.arguments[2].number for f in facts if f.match("plus", 3)
    }
    pos = positions([a, b, d])
    assert pos["2026-01-01T00:00:00Z"] < plus[a, d] < pos["2026-01-02T12:00:00Z"] < plus[b, d]


# --- placement edges ---


@pytest.mark.parametrize(
    ("a", "b"),
    [
        ("2026-01-01T24:00:00Z", "2026-01-02T00:00:00Z"),  # 24:00:00 is the next day's start
        ("2026-12-31T24:00:00Z", "2027-01-01T00:00:00Z"),
        ("2026-01-01T00:00:00.5Z", "2026-01-01T00:00:00.500000000Z"),
        ("2026-01-01T01:00:00+01:00", "2026-01-01T00:00:00Z"),
        ("2026-01-01T00:00:00-00:00", "2026-01-01T00:00:00Z"),
    ],
)
def test_same_instant(a: str, b: str) -> None:
    assert key(a, "dateTime") == key(b, "dateTime")


def test_beyond_microseconds() -> None:
    assert key("2026-01-01T00:00:00.1234567Z", "dateTime") > key(
        "2026-01-01T00:00:00.123456Z", "dateTime"
    )


def test_year_zero_and_negative_years() -> None:
    # XSD 1.1: 0000 is 1 BCE, a leap year, and -0001 the year before it.
    assert place("0000-02-29", XSD + "date") is not None
    assert key("0000-01-01T00:00:00Z", "dateTime") - key("-0001-12-31T23:59:59Z", "dateTime") == 1
    assert key("12026-01-01T00:00:00Z", "dateTime") > key("9999-12-31T23:59:59Z", "dateTime")


@pytest.mark.parametrize(
    ("lex", "local", "reason"),
    [
        ("1.5", "double", "value: xsd:double"),
        ("1.5", "float", "value: xsd:float"),
        ("2026-01-01T00:00:00", "dateTime", "value: dateTime without timezone"),
        ("2026-01-01Z", "date", "value: date with timezone"),
        ("P1MT1H", "duration", "value: mixed xsd:duration"),
        ("2026-01-01T00:00:00", "dateTimeStamp", "value: ill-typed xsd:dateTimeStamp"),
        ("2001-02-29", "date", "value: ill-typed xsd:date"),
        ("1900-02-29T00:00:00Z", "dateTime", "value: ill-typed xsd:dateTime"),
        ("2026-01-01T24:00:01Z", "dateTime", "value: ill-typed xsd:dateTime"),
        ("2026-01-01T00:00:00+14:01", "dateTime", "value: ill-typed xsd:dateTime"),
        ("02026-01-01", "date", "value: ill-typed xsd:date"),
        ("128", "byte", "value: ill-typed xsd:byte"),
        ("-1", "nonNegativeInteger", "value: ill-typed xsd:nonNegativeInteger"),
        ("0", "positiveInteger", "value: ill-typed xsd:positiveInteger"),
        ("1.0", "integer", "value: ill-typed xsd:integer"),
        ("\u0661", "integer", "value: ill-typed xsd:integer"),  # ARABIC-INDIC ONE: ASCII only
        (".", "decimal", "value: ill-typed xsd:decimal"),
        ("P", "duration", "value: ill-typed xsd:duration"),
        ("PT", "duration", "value: ill-typed xsd:duration"),
        ("P1Y", "dayTimeDuration", "value: ill-typed xsd:dayTimeDuration"),
        ("PT1H", "yearMonthDuration", "value: ill-typed xsd:yearMonthDuration"),
        ("yes", "boolean", "value: ill-typed xsd:boolean"),
    ],
)
def test_unplaceable(lex: str, local: str, reason: str) -> None:
    assert place(lex, XSD + local) == reason
    facts = value_facts([lit(lex, local)])
    assert facts == [Function("unplaceable", [lit(lex, local), String(reason)])]


@pytest.mark.parametrize(
    ("lex", "local", "space", "value"),
    [
        ("255", "unsignedByte", "numeric", 255),
        ("-128", "byte", "numeric", -128),
        ("+.5", "decimal", "numeric", Fraction(1, 2)),
        ("5.", "decimal", "numeric", 5),
        ("01", "integer", "numeric", 1),
        ("2026-01-01T00:00:00Z", "dateTimeStamp", "instant", Fraction(1767225600)),
        ("P1Y2M", "duration", "yearmonth", 14),
        ("-P2D", "duration", "daytime", -2 * 86400),
        ("PT0.5S", "dayTimeDuration", "daytime", Fraction(1, 2)),
        ("1", "boolean", "boolean", 1),
        ("false", "boolean", "boolean", 0),
    ],
)
def test_placed(lex: str, local: str, space: str, value: Fraction | int) -> None:
    placed = place(lex, XSD + local)
    assert isinstance(placed, Placed)
    assert (placed.space, placed.key) == (space, Fraction(value))


@pytest.mark.parametrize("local", ["string", "token", "anyURI"])
def test_unordered_datatypes_have_no_entry(local: str) -> None:
    assert place("x", XSD + local) is None
    assert value_facts([lit("x", local)]) == []
