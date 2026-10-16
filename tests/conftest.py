"""Wiring for the shared suite (spikes/README.md).

    uv run pytest                                    # the harness's own tests only
    uv run pytest --backend=<spike>                  # plus every vector against that spike
    uv run pytest --backend=all --scorecard          # every spike; record scorecards and journals
    uv run pytest --backend=<spike> --repeat=5       # median latency over five calls per vector

A scorecard is written only for a run that covered every vector, so filtering with `-k`
cannot overwrite a full record with a partial one.
"""

from __future__ import annotations

from functools import cache
from typing import cast

import pytest
from harness.backend import Session, Spike, discover
from harness.corpus import Vector, init_message, interpret_vectors
from harness.json_types import Obj
from harness.record import Result, summarise, write_scorecard

SPIKES_KEY = pytest.StashKey[list[Spike]]()
SESSIONS_KEY = pytest.StashKey[dict[str, Session]]()
RESULTS_KEY = pytest.StashKey[dict[str, list[Result]]]()
NO_SESSIONS: dict[str, Session] = {}  # when configuration failed before the stash was set
NO_RESULTS: dict[str, list[Result]] = {}


def pytest_addoption(parser: pytest.Parser) -> None:
    g = parser.getgroup("due2", "due2 spikes")
    g.addoption(
        "--backend",
        action="append",
        default=[],
        help="run the corpus against this spike (spikes/<name>); repeatable; 'all' for every spike",
    )
    g.addoption(
        "--scorecard",
        action="store_true",
        help="write spikes/<name>/scorecard.json and journal the run",
    )
    g.addoption("--repeat", type=int, default=1, help="calls per vector; latency is the median")


def pytest_configure(config: pytest.Config) -> None:
    names = cast(list[str], config.getoption("backend"))
    found = discover()
    if "all" in names:
        names = list(found)
    unknown = sorted(set(names) - found.keys())
    if unknown:
        raise pytest.UsageError(f"no spike {unknown} under spikes/ (have: {sorted(found)})")
    config.stash[SPIKES_KEY] = [found[n] for n in dict.fromkeys(names)]
    config.stash[SESSIONS_KEY] = {}
    config.stash[RESULTS_KEY] = {n: [] for n in names}


@cache
def vectors() -> list[Vector]:
    return interpret_vectors()


@cache
def init() -> Obj:
    return init_message()


def pytest_generate_tests(metafunc: pytest.Metafunc) -> None:
    if {"spike", "vector"} <= set(metafunc.fixturenames):
        pairs = [(s, v) for s in metafunc.config.stash[SPIKES_KEY] for v in vectors()]
        metafunc.parametrize(("spike", "vector"), pairs, ids=[f"{s.name}:{v.id}" for s, v in pairs])


@pytest.fixture
def session(spike: Spike, request: pytest.FixtureRequest) -> Session:
    sessions = request.config.stash[SESSIONS_KEY]
    if spike.name not in sessions:
        sessions[spike.name] = Session(spike, init())
    return sessions[spike.name]


@pytest.fixture
def record(request: pytest.FixtureRequest, spike: Spike) -> list[Result]:
    return request.config.stash[RESULTS_KEY][spike.name]


def pytest_terminal_summary(
    terminalreporter: pytest.TerminalReporter, config: pytest.Config
) -> None:
    sessions = config.stash.get(SESSIONS_KEY, NO_SESSIONS)
    for name, results in config.stash.get(RESULTS_KEY, NO_RESULTS).items():
        if not results:
            continue
        s = summarise(results)
        terminalreporter.write_line(
            f"{name}: {s['pass']} pass, {s['fail']} fail, {s['error']} error, "
            f"{s['unsupported']} unsupported of {s['vectors']}; "
            f"p50 {s.get('p50_ms', '-')} ms, p99 {s.get('p99_ms', '-')} ms"
        )
        if not config.getoption("scorecard"):
            continue
        if len(results) < len(vectors()):
            terminalreporter.write_line(f"{name}: partial run, scorecard not written")
            continue
        write_scorecard(sessions[name].spike, results, sessions[name].startup_ms)
        terminalreporter.write_line(f"{name}: scorecard written")


def pytest_unconfigure(config: pytest.Config) -> None:
    for s in config.stash.get(SESSIONS_KEY, NO_SESSIONS).values():
        s.close()
