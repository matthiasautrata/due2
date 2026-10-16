"""A JSON value type, so nothing in the harness is typed Any (ways-of-working.md §3)."""

from __future__ import annotations

import json
from typing import cast

type Json = bool | int | float | str | list[Json] | dict[str, Json] | None
type Obj = dict[str, Json]


def loads(text: str) -> Json:
    return cast(Json, json.loads(text))


def as_obj(value: Json, what: str) -> Obj:
    if not isinstance(value, dict):
        raise TypeError(f"{what}: expected an object, got {type(value).__name__}")
    return value


def as_list(value: Json, what: str) -> list[Json]:
    if not isinstance(value, list):
        raise TypeError(f"{what}: expected a list, got {type(value).__name__}")
    return value


def as_str(value: Json, what: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{what}: expected a string, got {type(value).__name__}")
    return value
