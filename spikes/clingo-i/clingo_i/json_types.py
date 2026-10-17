"""A JSON value type, so nothing in the spike is typed Any (ways-of-working.md §3).

`json.loads` returns `Any`. `loads` gives it the type `Json`, and each `as_` function narrows a
value to one shape, or raises `TypeError` naming where in the input it was. That error becomes an
`error` reply, so a malformed vector never reaches the program.
"""

from __future__ import annotations

import json
from typing import cast

type Json = bool | int | float | str | list[Json] | dict[str, Json] | None
type Obj = dict[str, Json]


def loads(text: str) -> Json:
    """`json.loads`, typed."""
    return cast(Json, json.loads(text))


def as_obj(value: Json, what: str) -> Obj:
    """`value` as an object; `what` is its path in the input, for the error message."""
    if not isinstance(value, dict):
        raise TypeError(f"{what}: expected an object, got {type(value).__name__}")
    return value


def as_list(value: Json, what: str) -> list[Json]:
    """`value` as a list; `what` is its path in the input, for the error message."""
    if not isinstance(value, list):
        raise TypeError(f"{what}: expected a list, got {type(value).__name__}")
    return value


def as_str(value: Json, what: str) -> str:
    """`value` as a string; `what` is its path in the input, for the error message."""
    if not isinstance(value, str):
        raise TypeError(f"{what}: expected a string, got {type(value).__name__}")
    return value
