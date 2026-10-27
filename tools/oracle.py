"""Ask clingo-i, the oracle, for the verdict and trace of one or more scenarios.

Two ways to name the input:

    uv run python tools/oracle.py CASE_DIR [--scenario NAME ...]
    uv run python tools/oracle.py --policy FILE [--policy FILE ...] SCENARIO ...

A case directory (`conformance/README.md`) gives its policies, its prefixes, and its
scenarios; `--scenario` picks some of them by name, and by default every one is asked. With
`--policy`, the policies are Turtle files evaluated together as one corpus, and each SCENARIO
is a JSON file holding one object `{"request", "sotw"}`, in the case format of
`conformance/README.md`, with an optional `"name"` (by default the file's path, or
`stdin line N`) and optional `"prefixes"`. A SCENARIO of `-` reads
such objects from stdin, one per line, so another process can stream scenarios through one
running backend. Prefixes add to `STANDARD_PREFIXES`; a name in `request` or `sotw` whose
prefix is declared nowhere is an error reply (#146).

Prints one JSON line per scenario, as soon as its reply arrives:
`{"scenario": name, "ms": wall time, "output": the trace}`, or `"error": text`, or
`"unsupported": the feature clingo-i declines` in place of `"output"`
(`spikes/README.md` § `interpret`). Exit status: 0 when every reply is an output, 1 when any
is an error or a decline, 2 for a usage or input error. clingo-i's stderr goes to
`spikes/clingo-i/.stderr.log`.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Iterator
from pathlib import Path

from harness.backend import ROOT, Reply, Session, load_spike
from harness.corpus import STANDARD_PREFIXES, case_vectors, init_message
from harness.json_types import Json, Obj, as_obj, as_str, loads

ORACLE = ROOT / "spikes" / "clingo-i"


def case_inputs(case_dir: Path, names: list[str]) -> Iterator[tuple[str, Obj]]:
    """(name, `interpret` input) for each scenario of the case, or of those in `names`."""
    vectors = case_vectors(case_dir)
    if not vectors:
        raise ValueError(f"{case_dir}: no scenarios (a negative case is not evaluated)")
    known = {as_str(v.input["scenario"], "scenario") for v in vectors}
    unknown = [n for n in names if n not in known]
    if unknown:
        raise ValueError(f"{case_dir}: no scenario named {unknown[0]!r}")
    for v in vectors:
        name = as_str(v.input["scenario"], "scenario")
        if not names or name in names:
            yield name, v.input


def file_inputs(policies: list[Path], scenarios: list[str]) -> Iterator[tuple[str, Obj]]:
    """(name, `interpret` input) for each scenario object in the files, `-` being stdin."""
    texts: list[Json] = [p.read_text() for p in policies]
    for source in scenarios:
        lines = sys.stdin if source == "-" else [Path(source).read_text()]
        for i, line in enumerate(lines, 1):
            if source == "-" and not line.strip():
                continue
            where = f"stdin line {i}" if source == "-" else source
            s = as_obj(loads(line), where)
            unknown = sorted(set(s) - {"name", "request", "sotw", "prefixes"})
            if unknown:
                raise ValueError(f"{where}: unknown field {unknown[0]!r}")
            missing = sorted({"request", "sotw"} - set(s))
            if missing:
                raise ValueError(f"{where}: no {missing[0]!r}")
            name = as_str(s.get("name", where), f"{where}: name")
            extra = as_obj(s.get("prefixes", {}), f"{where}: prefixes")
            prefixes: dict[str, Json] = {**STANDARD_PREFIXES, **extra}
            yield (
                name,
                {
                    "case": "oracle",
                    "scenario": name,
                    "policies": texts,
                    "prefixes": prefixes,
                    "request": s["request"],
                    "sotw": s["sotw"],
                },
            )


def reply_line(name: str, reply: Reply) -> Obj:
    """The printed form of one reply."""
    out: Obj = {"scenario": name, "ms": round(reply.ms, 2)}
    if reply.unsupported is not None:
        out["unsupported"] = reply.unsupported
    elif reply.error is not None:
        out["error"] = reply.error
    else:
        out["output"] = reply.output
    return out


def main(argv: list[str] | None = None) -> int:
    """Ask clingo-i every scenario named by `argv`; the exit status as the module states."""
    parser = argparse.ArgumentParser(description="Ask clingo-i for the trace of each scenario.")
    parser.add_argument("inputs", nargs="+", help="a case directory, or scenario files")
    parser.add_argument("--policy", action="append", type=Path, default=[])
    parser.add_argument("--scenario", action="append", default=[])
    args = parser.parse_args(argv)
    inputs: list[str] = args.inputs
    policies: list[Path] = args.policy
    scenario_names: list[str] = args.scenario
    if policies and scenario_names:
        parser.error("--scenario picks scenarios of a case directory, not of --policy files")
    if not policies and len(inputs) != 1:
        parser.error("without --policy, give exactly one case directory")

    try:
        if policies:
            scenarios = file_inputs(policies, inputs)
        else:
            scenarios = case_inputs(Path(inputs[0]), scenario_names)
        session = Session(load_spike(ORACLE), init_message())
        status = 0
        try:
            for name, payload in scenarios:
                reply = session.call("interpret", name, payload)
                print(json.dumps(reply_line(name, reply)), flush=True)
                if reply.output is None:
                    status = 1
        finally:
            session.close()
    except (OSError, ValueError) as e:
        print(f"oracle: {e}", file=sys.stderr)
        return 2
    return status


if __name__ == "__main__":
    raise SystemExit(main())
