"""Run one vector against one backend and classify the outcome — the only place that does.

`pass`: every repeat matches the expected result. `fail`: some repeat does not (a malformed
output is a mismatch, and so is an answer that changes between repeats). `error`: the backend
reported an error, crashed, or broke the protocol. `unsupported`: the task was not declared in
`ready`, which is never a pass.
"""

from __future__ import annotations

import statistics

from harness.backend import Session
from harness.compare import mismatches
from harness.corpus import Vector
from harness.record import Result


def run_interpret(session: Session, vector: Vector, repeat: int = 1) -> Result:
    session.ensure_started()
    if "interpret" not in session.tasks:
        return Result("interpret", vector.id, "unsupported", None, "")
    replies = [session.call("interpret", vector.id, vector.input) for _ in range(repeat)]
    ms = statistics.median(r.ms for r in replies)
    for r in replies:
        if r.error is not None:
            return Result("interpret", vector.id, "error", ms, r.error)
        diffs = mismatches(vector.expected, r.output, vector.prefixes)
        if diffs:
            return Result("interpret", vector.id, "fail", ms, "; ".join(diffs))
    return Result("interpret", vector.id, "pass", ms, "")
