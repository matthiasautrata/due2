"""The line protocol of spikes/README.md § Protocol: init, then one reply per call."""

from __future__ import annotations

import json
import sys

from clingo_i.interpret import Interpreter
from clingo_i.json_types import Json, Obj, as_obj, loads

TASKS = ["interpret"]


def send(message: Obj) -> None:
    print(json.dumps(message), flush=True)


def main() -> None:
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
