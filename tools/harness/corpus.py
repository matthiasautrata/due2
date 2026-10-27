"""Inputs and expected outputs of the `interpret` task, read from the conformance corpus.

One vector per positive scenario (conformance/README.md). Negative cases wait for W1
(issue #9) and are not vectors here. The profile modules go to a backend once, in the
init message, so a vector carries only its policies and scenario.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from check_corpus import CORE, MODULES, case_policies  # the registry, kept in one place

from harness.json_types import Json, Obj, as_list, as_obj, as_str, loads

ROOT = Path(__file__).resolve().parents[2]
CASES = ROOT / "conformance" / "cases"

STANDARD_PREFIXES: dict[str, str] = {
    "odrl": "http://www.w3.org/ns/odrl/2/",
    "dprod": "https://ekgf.org/dprod/spec/develop/",
    "due2": "https://w3id.org/due2/profile#",
    "xsd": "http://www.w3.org/2001/XMLSchema#",
}


@dataclass(frozen=True)
class Vector:
    id: str  # "<case>/<scenario>"
    input: Obj
    expected: Obj
    prefixes: dict[str, str]


def _rel(p: Path) -> str:
    return p.relative_to(ROOT).as_posix()


def init_message() -> Obj:
    """Every shipped profile module, its text, and which policy profile IRI selects it."""
    files = sorted({*CORE, *(f for fs in MODULES.values() for f in fs)})
    return {
        "modules": {_rel(f): f.read_text() for f in files},
        "core": [_rel(f) for f in CORE],
        "profiles": {iri: [_rel(f) for f in fs] for iri, fs in sorted(MODULES.items())},
    }


def interpret_vectors(cases: Path = CASES) -> list[Vector]:
    """One vector per positive scenario of every case under `cases`."""
    out: list[Vector] = []
    for case_dir in sorted(p for p in cases.iterdir() if (p / "case.json").is_file()):
        out.extend(case_vectors(case_dir))
    return out


def case_vectors(case_dir: Path) -> list[Vector]:
    """One vector per scenario of the case in `case_dir`; none for a negative case.

    A vector's prefixes are `STANDARD_PREFIXES` with the case's own over them.
    """
    case = as_obj(loads((case_dir / "case.json").read_text()), case_dir.name)
    if "expected_rejection" in case:
        return []
    prefixes = dict(STANDARD_PREFIXES)
    prefixes.update(
        {k: as_str(v, "prefix") for k, v in as_obj(case.get("prefixes", {}), "").items()}
    )
    policies: list[Json] = [p.read_text() for p in case_policies(case_dir)]
    out: list[Vector] = []
    seen: set[str] = set()
    for raw in as_list(case["scenarios"], f"{case_dir.name}.scenarios"):
        s = as_obj(raw, case_dir.name)
        name = as_str(s["name"], "scenario name")
        if name in seen:
            raise ValueError(f"{case_dir.name}: duplicate scenario name {name!r}")
        seen.add(name)
        vid = f"{case_dir.name}/{name}"
        prefix_json: dict[str, Json] = dict(prefixes)
        out.append(
            Vector(
                id=vid,
                input={
                    "case": case_dir.name,
                    "scenario": name,
                    "policies": policies,
                    "prefixes": prefix_json,
                    "request": s["request"],
                    "sotw": s["sotw"],
                },
                expected=as_obj(s["expected"], vid),
                prefixes=prefixes,
            )
        )
    return out
