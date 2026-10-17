"""A backend that knows nothing about ODRL, for the harness's own tests.

    python fake_backend.py MODE

- `echo`: answers every `interpret` call with the scenario's expected result, read straight
  from the case file — every vector must pass, which shows the protocol and the comparator agree.
- `verdict-only`: as `echo`, without `verdict_basis` and `eliminated` — a vector that asserts
  them is unsupported, never a pass; every other vector passes.
- `empty`: answers `{}` — every vector must fail, which shows a wrong answer is caught.
- `none`: declares no tasks — every vector is unsupported, never a pass.
- `decline`: declines every call, naming a feature — every vector is unsupported, never a pass.
- `error`: answers every call with an error.
- `crash`: exits on the first call.
- `wrong-id`: answers with another request's id.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

CASES = Path(__file__).resolve().parents[2] / "conformance" / "cases"


def expected(case: str, scenario: str) -> dict[str, object]:
    data = json.loads((CASES / case / "case.json").read_text())
    return next(s["expected"] for s in data["scenarios"] if s["name"] == scenario)


def main(mode: str) -> None:
    for line in sys.stdin:
        msg = json.loads(line)
        if "init" in msg:
            reply: dict[str, object] = {"ready": {"tasks": [] if mode == "none" else ["interpret"]}}
        elif mode == "crash":
            return
        else:
            vid, inp = msg["id"], msg["input"]
            if mode == "echo":
                reply = {"id": vid, "output": expected(inp["case"], inp["scenario"])}
            elif mode == "verdict-only":
                out = expected(inp["case"], inp["scenario"])
                for k in ("verdict_basis", "eliminated"):
                    out.pop(k, None)
                reply = {"id": vid, "output": out}
            elif mode == "empty":
                reply = {"id": vid, "output": {}}
            elif mode == "decline":
                reply = {"id": vid, "unsupported": "recurrence"}
            elif mode == "error":
                reply = {"id": vid, "error": "not implemented"}
            else:
                reply = {"id": vid + "-other", "output": {}}
        print(json.dumps(reply), flush=True)


if __name__ == "__main__":
    main(sys.argv[1])
