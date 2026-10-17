"""The line protocol of spikes/README.md § Protocol: init, then one reply per call.

Each line on stdin is one JSON message, and each reply one JSON line on stdout. The first message
is `{"init": …}`, answered `{"ready": {"tasks": ["interpret"]}}`. Every later message is a call,
`{"id", "task", "input"}`, answered with the same `id` and an output, a decline, or an error.
Diagnostics go to stderr, never stdout, so they cannot corrupt a reply.
"""

from __future__ import annotations

import json
import sys

from clingo_i.interpret import Interpreter
from clingo_i.json_types import Json, Obj, as_obj, loads

TASKS = ["interpret"]


def send(message: Obj) -> None:
    """Write one reply line, flushed, so the harness can read it before the next call."""
    print(json.dumps(message), flush=True)


def main() -> None:
    """Answer messages from stdin until it closes."""
    interpreter: Interpreter | None = None
    for line in sys.stdin:
        if not line.strip():
            continue
        message = as_obj(loads(line), "message")
        if "init" in message:
            interpreter = Interpreter(as_obj(message["init"], "init"))
            send({"ready": {"tasks": list[Json](TASKS)}})
            continue
        rid = message.get("id")
        task = message.get("task")
        if interpreter is None:
            reply: Obj = {"error": "call before init"}
        elif task not in TASKS:
            reply = {"error": f"task {task!r} is not declared"}
        else:
            reply = interpreter.reply(as_obj(message["input"], "input"))
        send({"id": rid, **reply})


if __name__ == "__main__":
    main()
