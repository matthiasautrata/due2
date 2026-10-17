"""The driver's value table (DESIGN.md § Values): value spaces, positions, and sums.

The program compares but never computes, and clingo's integers are 32-bit, so every
ordered literal reaches it as a position within its value space (decisions/0009 #4).
Nothing is truncated or rounded: a literal that cannot be placed exactly is reported.
"""

from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from fractions import Fraction

from clingo import Function, Number, String, Symbol, SymbolType

XSD = "http://www.w3.org/2001/XMLSchema#"
INT32 = 2**31
DAY = 86400

# xsd:integer and the types derived from it, with their ranges (XSD 1.1 Part 2 §3.4).
INTEGER_RANGES: dict[str, tuple[int | None, int | None]] = {
    "integer": (None, None),
    "nonNegativeInteger": (0, None),
    "positiveInteger": (1, None),
    "nonPositiveInteger": (None, 0),
    "negativeInteger": (None, -1),
    "long": (-(2**63), 2**63 - 1),
    "int": (-(2**31), 2**31 - 1),
    "short": (-(2**15), 2**15 - 1),
    "byte": (-(2**7), 2**7 - 1),
    "unsignedLong": (0, 2**64 - 1),
    "unsignedInt": (0, 2**32 - 1),
    "unsignedShort": (0, 2**16 - 1),
    "unsignedByte": (0, 2**8 - 1),
}

# Lexical spaces (XSD 1.1 Part 2 §3.3), ASCII digits only.
_D = "[0-9]"
DECIMAL = re.compile(rf"([+-]?)({_D}*)(?:\.({_D}*))?")
INTEGER = re.compile(rf"[+-]?{_D}+")
_DATE = rf"(-?(?:[1-9]{_D}{{3,}}|0{_D}{{3}}))-({_D}{{2}})-({_D}{{2}})"
_TZ = rf"(Z|[+-]{_D}{{2}}:{_D}{{2}})?"
DATETIME = re.compile(rf"{_DATE}T({_D}{{2}}):({_D}{{2}}):({_D}{{2}})(?:\.({_D}+))?{_TZ}")
DATE = re.compile(rf"{_DATE}{_TZ}")
DURATION = re.compile(
    rf"(-?)P(?:({_D}+)Y)?(?:({_D}+)M)?(?:({_D}+)D)?"
    rf"(T(?:({_D}+)H)?(?:({_D}+)M)?(?:({_D}+|{_D}*\.{_D}+)S)?)?"
)


@dataclass(frozen=True)
class Instant:
    """A dateTime in its own timezone: civil date, seconds since local midnight, offset."""

    year: int
    month: int
    day: int
    second: Fraction
    offset: int  # minutes east of UTC

    @property
    def key(self) -> Fraction:
        return (
            days_from_civil(self.year, self.month, self.day) * DAY + self.second - self.offset * 60
        )


@dataclass(frozen=True)
class Duration:
    months: int
    seconds: Fraction


@dataclass(frozen=True)
class Placed:
    space: str
    key: Fraction
    instant: Instant | None = None
    duration: Duration | None = None


# --- the calendar: proleptic Gregorian, astronomical years (XSD 1.1: 0000 is 1 BCE) ---


def leap(year: int) -> bool:
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)


def days_in_month(year: int, month: int) -> int:
    if month == 2:
        return 29 if leap(year) else 28
    return 30 if month in (4, 6, 9, 11) else 31


def days_from_civil(year: int, month: int, day: int) -> int:
    """Days since 1970-01-01 (H. Hinnant's algorithm; Python's // floors)."""
    y = year - (month <= 2)
    era = y // 400
    yoe = y - era * 400
    doy = (153 * (month + (-3 if month > 2 else 9)) + 2) // 5 + day - 1
    doe = yoe * 365 + yoe // 4 - yoe // 100 + doy
    return era * 146097 + doe - 719468


def civil_from_days(days: int) -> tuple[int, int, int]:
    z = days + 719468
    era = z // 146097
    doe = z - era * 146097
    yoe = (doe - doe // 1460 + doe // 36524 - doe // 146096) // 365
    doy = doe - (365 * yoe + yoe // 4 - yoe // 100)
    mp = (5 * doy + 2) // 153
    day = doy - (153 * mp + 2) // 5 + 1
    month = mp + 3 if mp < 10 else mp - 9
    return yoe + era * 400 + (month <= 2), month, day


# --- lexical forms to values; None when the form is not in the lexical space ---


def decimal(lex: str) -> Fraction | None:
    m = DECIMAL.fullmatch(lex)
    if m is None or not (m[2] or m[3]):
        return None
    frac = m[3] or ""
    value = Fraction(int(m[2] or "0") * 10 ** len(frac) + int(frac or "0"), 10 ** len(frac))
    return -value if m[1] == "-" else value


def _date(year: str, month: str, day: str) -> tuple[int, int, int] | None:
    y, mo, d = int(year), int(month), int(day)
    if not 1 <= mo <= 12 or not 1 <= d <= days_in_month(y, mo):
        return None
    return y, mo, d


def _offset(tz: str) -> int | None:
    """Minutes east of UTC, or None when out of range (XSD: at most 14:00 either way)."""
    if tz == "Z":
        return 0
    hours, minutes = int(tz[1:3]), int(tz[4:6])
    if minutes > 59 or hours > 14 or (hours == 14 and minutes > 0):
        return None
    return (-1 if tz[0] == "-" else 1) * (hours * 60 + minutes)


def date_time(lex: str) -> Instant | str | None:
    """The instant; the reason it has no place on the timeline; None when ill-typed."""
    m = DATETIME.fullmatch(lex)
    if m is None:
        return None
    date = _date(m[1], m[2], m[3])
    hour, minute, sec = int(m[4]), int(m[5]), int(m[6])
    frac = m[7] or ""
    offset = None if m[8] is None else _offset(m[8])
    if date is None or (m[8] is not None and offset is None) or minute > 59 or sec > 59:
        return None
    second = Fraction(sec) + Fraction(int(frac or "0"), 10 ** len(frac))
    if hour == 24:  # 24:00:00 is the first instant of the next day
        if minute or second:
            return None
        date = civil_from_days(days_from_civil(*date) + 1)
        hour = 0
    elif hour > 23:
        return None
    if offset is None:
        return "value: dateTime without timezone"
    return Instant(*date, hour * 3600 + minute * 60 + second, offset)


def duration(lex: str) -> tuple[Duration, bool, bool] | None:
    """The duration, and whether it has year-month and day-time components."""
    m = DURATION.fullmatch(lex)
    if m is None or not any(m.group(2, 3, 4, 6, 7, 8)) or (m[5] and not any(m.group(6, 7, 8))):
        return None
    sign = -1 if m[1] else 1
    months = int(m[2] or 0) * 12 + int(m[3] or 0)
    seconds = Fraction(int(m[4] or 0) * DAY + int(m[6] or 0) * 3600 + int(m[7] or 0) * 60) + (
        (decimal(m[8]) or 0) if m[8] else 0
    )
    return Duration(sign * months, sign * seconds), bool(m[2] or m[3]), bool(m[4] or m[5])


def _short(datatype: str) -> str:
    return "xsd:" + datatype.removeprefix(XSD) if datatype.startswith(XSD) else datatype


def place(lex: str, datatype: str) -> Placed | str | None:
    """The literal's space and value; or the reason it cannot be placed; or None when its
    datatype has no ordered space (strings, IRIs, tokens: compared only for equality)."""
    local = datatype.removeprefix(XSD) if datatype.startswith(XSD) else None
    ill = f"value: ill-typed {_short(datatype)}"
    if local in ("double", "float"):
        return f"value: xsd:{local}"
    if local in INTEGER_RANGES:
        if INTEGER.fullmatch(lex) is None:
            return ill
        n = int(lex)
        low, high = INTEGER_RANGES[local]
        if (low is not None and n < low) or (high is not None and n > high):
            return ill
        return Placed("numeric", Fraction(n))
    if local == "decimal":
        value = decimal(lex)
        return ill if value is None else Placed("numeric", value)
    if local in ("dateTime", "dateTimeStamp"):
        instant = date_time(lex)
        if instant is None or (local == "dateTimeStamp" and isinstance(instant, str)):
            return ill
        return instant if isinstance(instant, str) else Placed("instant", instant.key, instant)
    if local == "date":
        m = DATE.fullmatch(lex)
        date = None if m is None else _date(m[1], m[2], m[3])
        if m is None or date is None or (m[4] is not None and _offset(m[4]) is None):
            return ill
        if m[4] is not None:
            return "value: date with timezone"
        return Placed("date", Fraction(days_from_civil(*date)))
    if local in ("duration", "dayTimeDuration", "yearMonthDuration"):
        parsed = duration(lex)
        if parsed is None:
            return ill
        d, has_ym, has_dt = parsed
        if (local == "dayTimeDuration" and has_ym) or (local == "yearMonthDuration" and has_dt):
            return ill
        if has_ym and has_dt:
            return "value: mixed xsd:duration"
        if has_ym:
            return Placed("yearmonth", Fraction(d.months), duration=d)
        return Placed("daytime", d.seconds, duration=d)
    if local == "boolean":
        if lex not in ("true", "false", "1", "0"):
            return ill
        return Placed("boolean", Fraction(lex in ("true", "1")))
    return None


def add(instant: Instant, d: Duration) -> Fraction:
    """XSD 1.1 Part 2 Appendix E: months in the instant's own timezone, the day clamped to
    the end of the month, then the seconds. Returns the sum's place on the UTC timeline."""
    year, month0 = divmod(instant.year * 12 + instant.month - 1 + d.months, 12)
    month = month0 + 1
    day = min(instant.day, days_in_month(year, month))
    return Instant(year, month, day, instant.second, instant.offset).key + d.seconds


# --- the table ---


def literals(facts: Iterable[Symbol]) -> set[Symbol]:
    """Every lit(Lex, Datatype) term in the facts, at any depth."""

    def walk(s: Symbol) -> Iterator[Symbol]:
        if s.type == SymbolType.Function:
            if s.name == "lit" and len(s.arguments) == 2:
                yield s
            for a in s.arguments:
                yield from walk(a)

    return {lit for f in facts for lit in walk(f)}


def positions(space: str, keys: set[Fraction]) -> dict[Fraction, int]:
    """32-bit integers keep their value in the numeric space; everything else is a dense rank."""
    if space == "numeric" and all(k.denominator == 1 and -INT32 <= k < INT32 for k in keys):
        return {k: int(k) for k in keys}
    return {k: n for n, k in enumerate(sorted(keys))}


def value_facts(lits: Iterable[Symbol]) -> list[Symbol]:
    """value/3, plus/3, and unplaceable/2 for the literals of one vector."""
    out: list[Symbol] = []
    placed: dict[Symbol, Placed] = {}
    for lit in sorted(lits):
        result = place(lit.arguments[0].string, lit.arguments[1].string)
        if isinstance(result, str):
            out.append(Function("unplaceable", [lit, String(result)]))
        elif result is not None:
            placed[lit] = result
    sums = {
        (i, d): add(pi.instant, pd.duration)
        for i, pi in placed.items()
        if pi.instant is not None
        for d, pd in placed.items()
        if pd.duration is not None
    }
    keys: defaultdict[str, set[Fraction]] = defaultdict(set)
    for p in placed.values():
        keys[p.space].add(p.key)
    keys["instant"].update(sums.values())
    pos = {space: positions(space, ks) for space, ks in keys.items()}
    for lit, p in placed.items():
        out.append(Function("value", [lit, Function(p.space), Number(pos[p.space][p.key])]))
    for (i, d), key in sums.items():
        out.append(Function("plus", [i, d, Number(pos["instant"][key])]))
    return out
