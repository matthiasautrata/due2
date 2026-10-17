"""Run one vector against one backend and classify the outcome — the only place that does.

`pass`: every repeat matches the expected result. `fail`: some repeat does not (a malformed
output is a mismatch, and so is an answer that changes between repeats). `error`: the backend
reported an error, crashed, or broke the protocol. `unsupported`: the task was not declared in
`ready`, or the backend declined the vector and named the feature (`{"unsupported": "recurrence"}`,
the same on every repeat), or every repeat matches but lacks an explanation field the scenario
states (`verdict_basis`, `eliminated`, `verdict_range`, `unknown_parts`); never a pass.
"""

from __future__ import annotations

import statistics

from harness.backend import Session
from harness.compare import mismatches, unemitted
from harness.corpus import Vector
from harness.record import Result


def run_interpret(session: Session, vector: Vector, repeat: int = 1) -> Result:
    session.ensure_started()
    if "interpret" not in session.tasks:
        return Result("interpret", vector.id, "unsupported", None, "")
    replies = [session.call("interpret", vector.id, vector.input) for _ in range(repeat)]
    ms = statistics.median(r.ms for r in replies)
    declined = {r.unsupported for r in replies}
    if declined != {None}:
        if len(declined) == 1:
            return Result(
                "interpret", vector.id, "unsupported", ms, f"unsupported: {declined.pop()}"
            )
        return Result("interpret", vector.id, "fail", ms, "declined on some repeats only")
    lacking: set[tuple[str, ...]] = set()
    for r in replies:
        if r.error is not None:
            return Result("interpret", vector.id, "error", ms, r.error)
        diffs = mismatches(vector.expected, r.output, vector.prefixes)
        if diffs:
            return Result("interpret", vector.id, "fail", ms, "; ".join(diffs))
        lacking.add(tuple(unemitted(vector.expected, r.output)))
    if len(lacking) > 1:
        return Result(
            "interpret", vector.id, "fail", ms, "explanation emitted on some repeats only"
        )
    if missing := lacking.pop():
        return Result(
            "interpret", vector.id, "unsupported", ms, f"not emitted: {', '.join(missing)}"
        )
    return Result("interpret", vector.id, "pass", ms, "")
