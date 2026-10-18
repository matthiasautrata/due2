"""The harness's own tests: the comparator, the corpus reader, the protocol, the records.

These run on every commit. The fake backends (fixtures/fake_backend.py) pin the two ends:
a backend that returns the expected results passes every vector, and one that returns
nothing fails every vector.
"""

from __future__ import annotations

import json
import sys
from dataclasses import replace
from pathlib import Path

import pytest
from harness.backend import Session, Spike, discover, load_spike
from harness.compare import mismatches, unemitted
from harness.corpus import CASES, Vector, init_message, interpret_vectors
from harness.json_types import Obj, as_obj, loads
from harness.record import Result, journal, source_lines, summarise, write_scorecard
from harness.run import run_interpret

FAKE = Path(__file__).parent / "fixtures" / "fake_backend.py"
PFX = {"ex": "http://example.com/"}
GOOD: Obj = {
    "verdict": "Pending",
    "frontier": [["ex:pay", "ex:notify"], ["ex:delete"]],
    "obligations": [{"duty": "ex:pay", "status": "outstanding"}],
}


@pytest.fixture(scope="module")
def vectors() -> list[Vector]:
    return interpret_vectors()


@pytest.fixture(scope="module")
def init() -> Obj:
    return init_message()


def fake(tmp_path: Path, mode: str) -> Spike:
    return Spike("fake", tmp_path, [sys.executable, str(FAKE), mode], (), ())


# --- comparator ---------------------------------------------------------------------------


def test_identical_output_passes() -> None:
    assert mismatches(GOOD, GOOD, PFX) == []


def test_sets_ignore_order_and_prefixes_expand() -> None:
    got: Obj = {
        "verdict": "Pending",
        "frontier": [["http://example.com/delete"], ["ex:notify", "http://example.com/pay"]],
        "obligations": [{"duty": "http://example.com/pay", "status": "outstanding"}],
        "exact": True,  # not stated by the scenario, so not compared
    }
    assert mismatches(GOOD, got, PFX) == []


@pytest.mark.parametrize(
    ("change", "fragment"),
    [
        ({"verdict": "Permit"}, "verdict: expected Pending, got Permit"),
        ({"verdict": "Maybe"}, "not one of the five"),
        ({"frontier": [["ex:pay"], ["ex:delete"]]}, "frontier"),
        ({"frontier": [["ex:pay", "ex:notify"], ["ex:delete"], []]}, "frontier"),
        ({"obligations": []}, "obligations: missing"),
        ({"obligations": [{"duty": "ex:pay", "status": "done"}]}, "malformed output"),
        ({"frontier": "ex:pay"}, "malformed output"),
    ],
)
def test_differences_are_reported(change: Obj, fragment: str) -> None:
    assert any(fragment in m for m in mismatches(GOOD, GOOD | change, PFX))


def test_missing_keys_and_non_objects_are_malformed() -> None:
    assert mismatches(GOOD, {"verdict": "Pending"}, PFX)[0].startswith("malformed output")
    assert mismatches(GOOD, None, PFX)[0].startswith("malformed output")


def test_exact_is_compared_only_when_stated() -> None:
    want = GOOD | {"exact": False}
    assert mismatches(want, GOOD | {"exact": False}, PFX) == []
    assert mismatches(want, GOOD, PFX) == ["exact: expected False, got None"]


def test_obligation_instances_are_distinct() -> None:
    a: Obj = {
        **GOOD,
        "obligations": [{"duty": "ex:pay", "status": "outstanding", "instance": "2026-01-01"}],
    }
    assert mismatches(a, GOOD, PFX) != []


EXPLAINED: Obj = {
    **GOOD,
    "verdict_basis": [
        {"ref": "ex:read", "role": "permission"},
        {"ref": "ex:pay", "role": "duty"},
    ],
    "eliminated": [{"ref": "ex:read", "by": "ex:forbid", "rule": "prohibit"}],
    "unknown_parts": [{"ref": "ex:read", "input": "ex:purpose", "status": "missing"}],
}


def test_explanation_is_compared_as_sets_when_stated_and_emitted() -> None:
    reordered: Obj = {
        **EXPLAINED,
        "verdict_basis": [
            {"ref": "http://example.com/pay", "role": "duty"},
            {"ref": "ex:read", "role": "permission"},
        ],
    }
    assert mismatches(EXPLAINED, reordered, PFX) == []
    assert mismatches(GOOD, EXPLAINED, PFX) == []  # not stated: not compared
    assert mismatches(EXPLAINED, GOOD, PFX) == []  # not emitted: unemitted's business
    assert unemitted(EXPLAINED, GOOD) == ["verdict_basis", "eliminated", "unknown_parts"]
    assert unemitted(EXPLAINED, EXPLAINED) == []
    assert unemitted(GOOD, GOOD) == []


@pytest.mark.parametrize(
    ("change", "fragment"),
    [
        ({"verdict_basis": [{"ref": "ex:read", "role": "permission"}]}, "verdict_basis: missing"),
        ({"verdict_basis": [{"ref": "ex:read", "role": "ready"}]}, "malformed output"),
        ({"eliminated": []}, "eliminated: missing"),
        ({"eliminated": [{"ref": "ex:read", "rule": "prohibit"}]}, "malformed output"),
        ({"unknown_parts": []}, "unknown_parts: missing"),
        (
            {"unknown_parts": [{"ref": "ex:read", "input": "ex:purpose", "status": "absent"}]},
            "malformed output",
        ),
    ],
)
def test_explanation_differences_are_reported(change: Obj, fragment: str) -> None:
    assert any(fragment in m for m in mismatches(EXPLAINED, EXPLAINED | change, PFX))


# --- corpus -------------------------------------------------------------------------------


def test_one_vector_per_positive_scenario(vectors: list[Vector]) -> None:
    want: list[str] = []
    for case_dir in sorted(CASES.iterdir()):
        if (case_dir / "case.json").is_file():
            case = json.loads((case_dir / "case.json").read_text())
            if "expected_rejection" not in case:
                want += [f"{case_dir.name}/{s['name']}" for s in case["scenarios"]]
    assert [v.id for v in vectors] == want
    assert len(set(want)) == len(want)


def test_vector_inputs_are_self_contained(vectors: list[Vector], init: Obj) -> None:
    modules = as_obj(init["modules"], "modules")
    for v in vectors:
        assert set(v.input) == {
            "case",
            "scenario",
            "policy",
            "prefixes",
            "request",
            "sotw",
            "config",
        }
        assert set(v.expected) >= {"verdict", "frontier", "obligations"}
    for files in as_obj(init["profiles"], "profiles").values():
        assert isinstance(files, list)
        assert all(f in modules for f in files)


def test_every_expected_result_is_well_formed(vectors: list[Vector]) -> None:
    for v in vectors:
        assert mismatches(v.expected, v.expected, v.prefixes) == [], v.id


# --- spikes and the protocol --------------------------------------------------------------


def test_backend_toml(tmp_path: Path) -> None:
    d = tmp_path / "spikes" / "demo"
    d.mkdir(parents=True)
    (d / "backend.toml").write_text(
        'command = ["python3", "main.py"]\n'
        'sources = ["*.py"]\n'
        "[[check]]\n"
        'name = "lint"\n'
        'command = ["ruff", "check", "."]\n'
        "count = '^\\S+:\\d+:'\n"
    )
    (d / "main.py").write_text("x = 1\n\n# two non-blank lines\n")
    (tmp_path / "spikes" / "not-a-spike").mkdir()
    assert list(discover(tmp_path / "spikes")) == ["demo"]
    s = load_spike(d)
    assert s.command == ["python3", "main.py"]
    assert not s.exact_only
    assert [(c.name, c.command, c.count) for c in s.checks] == [
        ("lint", ["ruff", "check", "."], r"^\S+:\d+:")
    ]
    assert source_lines(s) == 2


def test_echo_backend_passes_every_vector(tmp_path: Path, vectors: list[Vector], init: Obj) -> None:
    session = Session(fake(tmp_path, "echo"), init)
    try:
        results = [run_interpret(session, v) for v in vectors]
    finally:
        session.close()
    assert [r for r in results if r.status != "pass"] == []
    assert len(session.startup_ms) == 1


def test_exact_only_backend_is_not_asked_for_the_fallback(
    tmp_path: Path, vectors: list[Vector], init: Obj
) -> None:
    # Without the flag, a slow-mode backend fails the beyond-max_mixed scenario that its exact
    # answer contradicts (due2-max-mixed, scenario 1), though it computes what the spec defines.
    session = Session(replace(fake(tmp_path, "echo"), exact_only=True), init)
    try:
        results = {v.id: run_interpret(session, v) for v in vectors}
    finally:
        session.close()
    fallback = {v.id for v in vectors if v.expected.get("exact") is False}
    assert fallback
    for vid, r in results.items():
        if vid in fallback:
            assert (r.status, r.detail) == ("unsupported", "unsupported: max_mixed fallback")
        else:
            assert r.status == "pass"


def test_empty_backend_fails_every_vector(tmp_path: Path, vectors: list[Vector], init: Obj) -> None:
    session = Session(fake(tmp_path, "empty"), init)
    try:
        results = [run_interpret(session, v) for v in vectors]
    finally:
        session.close()
    assert {r.status for r in results} == {"fail"}


def test_unemitted_explanation_is_unsupported_never_a_pass(
    tmp_path: Path, vectors: list[Vector], init: Obj
) -> None:
    session = Session(fake(tmp_path, "verdict-only"), init)
    try:
        results = {r.vector: r for r in (run_interpret(session, v) for v in vectors)}
    finally:
        session.close()
    explained = {v.id for v in vectors if set(v.expected) & {"verdict_basis", "eliminated"}}
    assert explained
    for vid, r in results.items():
        if vid in explained:
            assert (r.status, r.detail.startswith("not emitted: ")) == ("unsupported", True)
        else:
            assert r.status == "pass"


@pytest.mark.parametrize(
    ("mode", "status", "fragment"),
    [
        ("none", "unsupported", ""),
        ("decline", "unsupported", "unsupported: recurrence"),
        ("error", "error", "not implemented"),
        ("crash", "error", "crash: backend exited"),
        ("wrong-id", "error", "protocol: reply id"),
    ],
)
def test_backend_faults(
    tmp_path: Path, vectors: list[Vector], init: Obj, mode: str, status: str, fragment: str
) -> None:
    session = Session(fake(tmp_path, mode), init)
    try:
        results = [run_interpret(session, v) for v in vectors[:3]]
    finally:
        session.close()
    assert all(r.status == status and fragment in r.detail for r in results)
    if mode in {"crash", "wrong-id"}:
        assert len(session.startup_ms) == 3  # restarted after each fault


# --- scorecard and journal ----------------------------------------------------------------


def test_scorecard_and_journal(tmp_path: Path) -> None:
    spike = fake(tmp_path, "echo")
    results = [
        Result("interpret", "c/a", "pass", 2.0, ""),
        Result("interpret", "c/b", "fail", 4.0, "verdict: expected Permit, got Deny"),
        Result("interpret", "c/c", "unsupported", None, ""),
    ]
    card = write_scorecard(spike, results, [120.0])
    saved = as_obj(loads((tmp_path / "scorecard.json").read_text()), "scorecard")
    assert saved == card
    task = as_obj(as_obj(saved["tasks"], "tasks")["interpret"], "interpret")
    assert task["summary"] == summarise(results)
    assert task["summary"] == {
        "vectors": 3,
        "pass": 1,
        "fail": 1,
        "error": 0,
        "unsupported": 1,
        "total_ms": 6.0,
        "p50_ms": 3.0,
        "p95_ms": 3.9,
        "p99_ms": 3.98,
        "max_ms": 4.0,
    }
    items = as_obj(task["items"], "items")
    assert as_obj(items["c/b"], "c/b")["detail"] == "verdict: expected Permit, got Deny"
    write_scorecard(spike, results, [110.0])
    runs = journal(spike)
    assert [e["kind"] for e in runs] == ["run", "run"]
    assert all(e["pass"] == 1 and "revision" in e and "at" in e for e in runs)
