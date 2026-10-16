"""main.py speaks the line protocol of spikes/README.md."""

from __future__ import annotations

import json
import subprocess
import sys

from clingo_i.json_types import Obj
from tests.conftest import INIT, SPIKE, vector


def test_init_and_one_call() -> None:
    lines: list[Obj] = [{"init": INIT}, {"id": "test/one", "task": "interpret", "input": vector()}]
    done = subprocess.run(
        [sys.executable, "main.py"],
        cwd=SPIKE,
        input="".join(json.dumps(m) + "\n" for m in lines),
        capture_output=True,
        text=True,
        check=True,
        timeout=60,
    )
    ready, reply = (json.loads(line) for line in done.stdout.splitlines())
    assert ready == {"ready": {"tasks": ["interpret"]}}
    assert reply["id"] == "test/one"
    assert reply["output"]["verdict"] == "Permit"


def test_unknown_task_is_an_error() -> None:
    lines: list[Obj] = [{"init": INIT}, {"id": "x", "task": "w2", "input": {}}]
    done = subprocess.run(
        [sys.executable, "main.py"],
        cwd=SPIKE,
        input="".join(json.dumps(m) + "\n" for m in lines),
        capture_output=True,
        text=True,
        check=True,
        timeout=60,
    )
    reply = json.loads(done.stdout.splitlines()[1])
    assert reply["id"] == "x" and "error" in reply
