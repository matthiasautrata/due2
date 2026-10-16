"""Record what a spike cost, and compare spikes (spikes/README.md).

    uv run python tools/spike_journal.py log <spike> <kind> "<summary>" [--minutes N] [--vector ID] [--by WHO]
    uv run python tools/spike_journal.py check <spike>
    uv run python tools/spike_journal.py summary [<spike> ...]

`log` appends one entry to `spikes/<spike>/journal.jsonl`. Kinds: `session` (a stretch of
work; give --minutes), `attempt` (a try at a vector or feature that is then tested),
`rewrite` (a component thrown away and redone), `bug` (a defect found after code was
believed right; give --vector when a vector found it), `note`.

`check` runs the spike's declared checkers (its backend.toml `[[check]]` entries) and
journals each one's exit code, diagnostic count, and duration: the compiler and checker
complaints, counted the same way every time.

`summary` prints a Markdown table: source size, effort, and the latest scorecard, one row
per spike. Test runs are journalled by `pytest --backend=<spike> --scorecard`.
"""

from __future__ import annotations

import argparse
import re
import statistics
import subprocess
import sys
import time

from harness.backend import Spike, discover
from harness.json_types import Json, Obj, as_obj, loads
from harness.record import append_journal, journal, scorecard_path, source_lines

KINDS = ("session", "attempt", "rewrite", "bug", "note")


def spike_named(name: str) -> Spike:
    spikes = discover()
    if name not in spikes:
        sys.exit(f"no spike {name!r} under spikes/ (have: {sorted(spikes)})")
    return spikes[name]


def cmd_log(args: argparse.Namespace) -> None:
    entry: Obj = {"kind": args.kind, "summary": args.summary}
    if args.minutes is not None:
        entry["minutes"] = args.minutes
    if args.vector is not None:
        entry["vector"] = args.vector
    if args.by is not None:
        entry["by"] = args.by
    append_journal(spike_named(args.spike), entry)


def cmd_check(args: argparse.Namespace) -> None:
    spike = spike_named(args.spike)
    if not spike.checks:
        sys.exit(f"{spike.name}: backend.toml declares no [[check]]")
    for check in spike.checks:
        t0 = time.perf_counter()
        proc = subprocess.run(  # noqa: S603 — the spike's own declared checker
            check.command, cwd=spike.dir, capture_output=True, text=True, check=False
        )
        ms = (time.perf_counter() - t0) * 1000
        lines = (proc.stdout + proc.stderr).splitlines()
        count = (
            sum(1 for line in lines if re.search(check.count, line))
            if check.count is not None
            else (0 if proc.returncode == 0 else 1)
        )
        append_journal(
            spike,
            {
                "kind": "check",
                "name": check.name,
                "exit": proc.returncode,
                "diagnostics": count,
                "ms": round(ms),
            },
        )
        print(f"{spike.name} {check.name}: exit {proc.returncode}, {count} diagnostics")


def _num(value: Json) -> float:
    return float(value) if isinstance(value, int | float) else 0.0


def row(spike: Spike) -> list[str]:
    entries = journal(spike)

    def kind(k: str) -> list[Obj]:
        return [e for e in entries if e.get("kind") == k]

    checks = kind("check")
    latest: dict[str, Obj] = {str(c["name"]): c for c in checks}
    cells = [
        spike.name,
        str(source_lines(spike)),
        f"{sum(_num(e.get('minutes')) for e in entries):.0f}",
        str(len(kind("session"))),
        str(len(kind("attempt"))),
        str(len(kind("rewrite"))),
        str(len(kind("bug"))),
        str(len(kind("run"))),
        f"{sum(_num(c['diagnostics']) for c in checks):.0f}",
        f"{sum(_num(c['diagnostics']) for c in latest.values()):.0f}",
    ]
    path = scorecard_path(spike)
    if not path.is_file():
        return [*cells, "-", "-", "-", "-"]
    card = as_obj(loads(path.read_text()), str(path))
    task = as_obj(as_obj(card["tasks"], "tasks").get("interpret", {}), "interpret")
    s = as_obj(task.get("summary", {}), "summary")
    startup = [_num(x) for x in card["startup_ms"]] if isinstance(card["startup_ms"], list) else []
    return [
        *cells,
        f"{s.get('pass', 0)}/{s.get('vectors', 0)}",
        str(s.get("p50_ms", "-")),
        str(s.get("p99_ms", "-")),
        f"{statistics.median(startup):.0f}" if startup else "-",
    ]


HEADER = [
    "spike",
    "lines",
    "minutes",
    "sessions",
    "attempts",
    "rewrites",
    "bugs",
    "test runs",
    "diagnostics (all)",
    "diagnostics (now)",
    "interpret pass",
    "p50 ms",
    "p99 ms",
    "startup ms",
]


def cmd_summary(args: argparse.Namespace) -> None:
    spikes = [spike_named(n) for n in args.spikes] if args.spikes else list(discover().values())
    print("| " + " | ".join(HEADER) + " |")
    print("|" + "---|" * len(HEADER))
    for s in spikes:
        print("| " + " | ".join(row(s)) + " |")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    sub = p.add_subparsers(required=True)
    log = sub.add_parser("log", help="journal one entry")
    log.add_argument("spike")
    log.add_argument("kind", choices=KINDS)
    log.add_argument("summary")
    log.add_argument("--minutes", type=int)
    log.add_argument("--vector")
    log.add_argument("--by", help="who did the work: a person, or a model id")
    log.set_defaults(fn=cmd_log)
    check = sub.add_parser("check", help="run the spike's checkers and journal the counts")
    check.add_argument("spike")
    check.set_defaults(fn=cmd_check)
    summary = sub.add_parser("summary", help="compare spikes as a Markdown table")
    summary.add_argument("spikes", nargs="*")
    summary.set_defaults(fn=cmd_summary)
    args = p.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
