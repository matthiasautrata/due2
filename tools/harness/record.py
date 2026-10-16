"""Scorecards and journals: what a spike scored, and what it cost to get there.

`spikes/<name>/scorecard.json` — the last recorded run, per task and per vector:
status, latency, and a summary. Overwritten by `pytest --backend=<name> --scorecard`.

`spikes/<name>/journal.jsonl` — append-only, one JSON object per line: work sessions,
attempts, rewrites, bugs, checker runs, and test runs (spikes/README.md). Written by
`tools/spike_journal.py` and by the scorecard writer.

A scorecard is a snapshot, so it is overwritten; the journal is the history, so it only grows.
"""

from __future__ import annotations

import json
import platform
import statistics
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from harness.backend import ROOT, Spike
from harness.json_types import Json, Obj, as_obj, loads

STATUSES = ("pass", "fail", "error", "unsupported")


@dataclass(frozen=True)
class Result:
    task: str
    vector: str
    status: str  # one of STATUSES
    ms: float | None  # median over repeats; None when unsupported
    detail: str  # first mismatch or the error, empty on pass


def now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def revision() -> str:
    def git(*args: str) -> str:
        return subprocess.run(  # noqa: S603
            ["git", *args],  # noqa: S607
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        ).stdout.strip()

    sha = git("rev-parse", "--short", "HEAD")
    return sha + ("+dirty" if git("status", "--porcelain") else "")


def append_journal(spike: Spike, entry: Obj) -> None:
    line = json.dumps({"at": now(), **entry}, sort_keys=True, ensure_ascii=False)
    with (spike.dir / "journal.jsonl").open("a") as f:
        f.write(line + "\n")


def _pct(xs: list[float], q: float) -> float:
    if len(xs) == 1:
        return xs[0]
    return statistics.quantiles(xs, n=100, method="inclusive")[round(q * 100) - 1]


def summarise(results: list[Result]) -> Obj:
    counts: dict[str, Json] = {s: sum(r.status == s for r in results) for s in STATUSES}
    times = sorted(r.ms for r in results if r.ms is not None and r.status != "unsupported")
    out: Obj = {"vectors": len(results), **counts}
    if times:
        out |= {
            "total_ms": round(sum(times), 1),
            "p50_ms": round(_pct(times, 0.50), 2),
            "p95_ms": round(_pct(times, 0.95), 2),
            "p99_ms": round(_pct(times, 0.99), 2),  # ways-of-working.md §10.4
            "max_ms": round(times[-1], 2),
        }
    return out


def _item(r: Result) -> Json:
    item: Obj = {"status": r.status, "ms": None if r.ms is None else round(r.ms, 2)}
    if r.detail:
        item["detail"] = r.detail
    return item


def write_scorecard(spike: Spike, results: list[Result], startup_ms: list[float]) -> Obj:
    """Overwrite the spike's scorecard and journal one `run` entry per task."""
    rev = revision()
    tasks: Obj = {}
    for task in sorted({r.task for r in results}):
        rs = sorted((r for r in results if r.task == task), key=lambda r: r.vector)
        summary = summarise(rs)
        tasks[task] = {"summary": summary, "items": {r.vector: _item(r) for r in rs}}
        append_journal(spike, {"kind": "run", "task": task, "revision": rev, **summary})
    card: Obj = {
        "spike": spike.name,
        "revision": rev,
        "recorded_at": now(),
        "machine": f"{platform.system()} {platform.machine()} · Python {platform.python_version()}",
        "startup_ms": [round(x, 1) for x in startup_ms],
        "tasks": tasks,
    }
    scorecard_path(spike).write_text(
        json.dumps(card, indent=1, sort_keys=True, ensure_ascii=False) + "\n"
    )
    return card


def source_lines(spike: Spike) -> int:
    """Non-blank lines in the spike's declared sources: the size compared at the end."""
    files = {p for g in spike.sources for p in spike.dir.glob(g) if p.is_file()}
    return sum(
        sum(1 for line in p.read_text(errors="replace").splitlines() if line.strip()) for p in files
    )


def journal(spike: Spike) -> list[Obj]:
    path = spike.dir / "journal.jsonl"
    if not path.is_file():
        return []
    return [
        as_obj(loads(line), f"{path}:{n}")
        for n, line in enumerate(path.read_text().splitlines(), 1)
        if line.strip()
    ]


def scorecard_path(spike: Spike) -> Path:
    return spike.dir / "scorecard.json"
