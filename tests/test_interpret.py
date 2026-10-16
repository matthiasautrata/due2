"""Every corpus vector against every selected spike (`--backend`); no spike, no tests."""

from __future__ import annotations

from typing import cast

import pytest
from harness.backend import Session
from harness.corpus import Vector
from harness.record import Result
from harness.run import run_interpret


def test_interpret(
    session: Session, vector: Vector, record: list[Result], request: pytest.FixtureRequest
) -> None:
    result = run_interpret(session, vector, cast(int, request.config.getoption("repeat")))
    record.append(result)
    if result.status == "unsupported":
        pytest.skip(result.detail or "interpret not declared")
    assert result.status == "pass", result.detail
