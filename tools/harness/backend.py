"""Discover spikes and talk to one over the line protocol of spikes/README.md.

A spike is a directory with a `backend.toml`. Its `command` runs with the spike
directory as working directory, reads JSON lines on stdin, and answers one JSON line
per request on stdout:

  -> {"init": {...}}                          <- {"ready": {"tasks": ["interpret", ...]}}
  -> {"id": ..., "task": ..., "input": {...}} <- {"id": ..., "output": {...}}
                                               | {"id": ..., "error": "..."}
                                               | {"id": ..., "unsupported": "<feature>"}

Timing is wall clock, measured here, the same way for every backend: startup is spawn
to `ready` (it includes loading the profile modules); a call is write to reply.
"""

from __future__ import annotations

import json
import selectors
import subprocess
import time
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import IO, cast

from harness.json_types import Json, Obj, as_list, as_obj, as_str, loads

ROOT = Path(__file__).resolve().parents[2]
SPIKES = ROOT / "spikes"
CALL_TIMEOUT_S = 60.0
STARTUP_TIMEOUT_S = 120.0


@dataclass(frozen=True)
class Check:
    name: str
    command: list[str]
    count: str | None  # regex; matching output lines are counted as diagnostics


@dataclass(frozen=True)
class Spike:
    name: str
    dir: Path
    command: list[str]
    checks: tuple[Check, ...]
    sources: tuple[str, ...]  # globs, relative to the spike: the code that counts as its size
    # Completes unknowns exactly and has no beyond-max_mixed fallback (decisions/0009 #5).
    exact_only: bool = False


def load_spike(directory: Path) -> Spike:
    with (directory / "backend.toml").open("rb") as f:
        cfg = cast(Obj, tomllib.load(f))
    checks = tuple(
        Check(
            name=as_str(c["name"], "check.name"),
            command=[as_str(x, "check.command") for x in as_list(c["command"], "check")],
            count=as_str(c["count"], "check.count") if "count" in c else None,
        )
        for c in (as_obj(x, "check") for x in as_list(cfg.get("check", []), "check"))
    )
    return Spike(
        name=directory.name,
        dir=directory,
        command=[as_str(x, "command") for x in as_list(cfg["command"], "command")],
        checks=checks,
        sources=tuple(as_str(x, "sources") for x in as_list(cfg.get("sources", []), "sources")),
        exact_only=cfg.get("exact_only", False) is True,
    )


def discover(root: Path = SPIKES) -> dict[str, Spike]:
    if not root.is_dir():
        return {}
    return {p.name: load_spike(p) for p in sorted(root.iterdir()) if (p / "backend.toml").is_file()}


@dataclass(frozen=True)
class Reply:
    output: Json | None
    error: str | None
    ms: float
    unsupported: str | None = None  # the feature the backend declines this vector for


class BackendCrashed(Exception):
    pass


@dataclass
class Session:
    """One running backend process. Restarted after a crash or timeout."""

    spike: Spike
    init: Obj
    tasks: frozenset[str] = frozenset()
    startup_ms: list[float] = field(default_factory=list[float])
    _proc: subprocess.Popen[str] | None = None

    def _start(self) -> None:
        log = (self.spike.dir / ".stderr.log").open("a")
        t0 = time.perf_counter()
        self._proc = subprocess.Popen(  # noqa: S603 — the spike's own declared command
            self.spike.command,
            cwd=self.spike.dir,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=log,
            text=True,
            bufsize=1,
        )
        ready = as_obj(self._exchange({"init": self.init}, STARTUP_TIMEOUT_S), "ready reply")
        info = as_obj(ready["ready"], "ready")
        self.tasks = frozenset(as_str(t, "task") for t in as_list(info["tasks"], "tasks"))
        self.startup_ms.append((time.perf_counter() - t0) * 1000)

    def _exchange(self, message: Obj, timeout: float) -> Json:
        proc = self._proc
        if proc is None or proc.stdin is None or proc.stdout is None:
            raise BackendCrashed("backend not running")
        try:
            proc.stdin.write(json.dumps(message) + "\n")
            proc.stdin.flush()
        except BrokenPipeError as e:
            self.close()
            raise BackendCrashed("backend closed its input") from e
        line = _readline(proc.stdout, timeout)
        if line is None:
            self.close()
            raise BackendCrashed(f"no reply within {timeout:.0f}s")
        if not line:
            self.close()
            raise BackendCrashed("backend exited")
        return loads(line)

    def ensure_started(self) -> None:
        if self._proc is None or self._proc.poll() is not None:
            self._start()

    def call(self, task: str, vid: str, payload: Obj) -> Reply:
        self.ensure_started()
        t0 = time.perf_counter()
        try:
            raw = self._exchange({"id": vid, "task": task, "input": payload}, CALL_TIMEOUT_S)
        except BackendCrashed as e:
            return Reply(None, f"crash: {e}", (time.perf_counter() - t0) * 1000)
        ms = (time.perf_counter() - t0) * 1000
        reply = as_obj(raw, "reply")
        if reply.get("id") != vid:
            self.close()
            return Reply(None, f"protocol: reply id {reply.get('id')!r} for {vid!r}", ms)
        if "error" in reply:
            return Reply(None, as_str(reply["error"], "error"), ms)
        if "unsupported" in reply:
            feature = as_str(reply["unsupported"], "unsupported")
            if not feature:
                return Reply(None, "protocol: unsupported names no feature", ms)
            return Reply(None, None, ms, feature)
        return Reply(reply.get("output"), None, ms)

    def close(self) -> None:
        proc, self._proc = self._proc, None
        if proc is None:
            return
        if proc.stdin is not None:
            proc.stdin.close()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()


def _readline(stream: IO[str], timeout: float) -> str | None:
    """A line, "" at end of stream, or None on timeout."""
    sel = selectors.DefaultSelector()
    sel.register(stream, selectors.EVENT_READ)
    try:
        if not sel.select(timeout):
            return None
        return stream.readline()
    finally:
        sel.close()
