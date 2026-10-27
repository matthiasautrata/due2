"""Compare a backend's `interpret` output with a scenario's expected result.

Output shape (spikes/README.md):
  {"verdict": str, "frontier": [[duty IRI, ...], ...],
   "obligations": [{"duty": IRI, "status": str, "instance"?: dateTime}], "exact"?: bool,
   "frontier_complete"?: bool,
   "verdict_basis"?: [{"ref": IRI, "role": str}], "eliminated"?: [{"ref": IRI, "by": IRI, "rule": str}],
   "verdict_range"?: {"low": str, "high": str},
   "unknown_parts"?: [{"ref": IRI, "input": IRI, "status": str}]}

The frontier is a set of sets; obligations, the basis, the eliminations, and the unknown parts
are sets. `exact` is compared only where the scenario states it (conformance/README.md). The
explanation fields and `frontier_complete` are compared only where the scenario states them and
the output has them; `unemitted` names the ones a scenario states and the output lacks.
Prefixed names are expanded on both sides.
"""

from __future__ import annotations

from harness.json_types import Json, Obj, as_list, as_obj, as_str

VERDICTS = frozenset({"Permit", "Deny", "Pending", "NotApplicable", "Indeterminate"})
STATUSES = frozenset({"fulfilled", "outstanding", "violated", "unknown"})
ROLES = frozenset({"prohibition", "permission", "duty", "unknown", "obligation", "closed"})
PART_STATUSES = frozenset({"missing", "invalid", "conflict", "unresolved", "misfit"})
EXPLANATION = ("verdict_basis", "eliminated", "verdict_range", "unknown_parts")
# Compared like the explanation: where the scenario states it and the output has it.
OPTIONAL = (*EXPLANATION, "frontier_complete")

type Obligation = tuple[str, str, str | None]


def expand(name: str, prefixes: dict[str, str]) -> str:
    if name.startswith(("http://", "https://", "urn:")):
        return name
    pfx, sep, local = name.partition(":")
    return prefixes[pfx] + local if sep and pfx in prefixes else name


def _frontier(value: Json, prefixes: dict[str, str]) -> frozenset[frozenset[str]]:
    return frozenset(
        frozenset(expand(as_str(d, "duty"), prefixes) for d in as_list(alt, "alternative"))
        for alt in as_list(value, "frontier")
    )


def _obligations(value: Json, prefixes: dict[str, str]) -> frozenset[Obligation]:
    out: set[Obligation] = set()
    for raw in as_list(value, "obligations"):
        o = as_obj(raw, "obligation")
        status = as_str(o["status"], "status")
        if status not in STATUSES:
            raise ValueError(f"unknown obligation status {status!r}")
        inst = o.get("instance")
        out.add(
            (
                expand(as_str(o["duty"], "duty"), prefixes),
                status,
                None if inst is None else as_str(inst, "instance"),
            )
        )
    return frozenset(out)


def _basis(value: Json, prefixes: dict[str, str]) -> frozenset[tuple[str, str]]:
    out: set[tuple[str, str]] = set()
    for raw in as_list(value, "verdict_basis"):
        b = as_obj(raw, "basis entry")
        role = as_str(b["role"], "role")
        if role not in ROLES:
            raise ValueError(f"unknown basis role {role!r}")
        out.add((expand(as_str(b["ref"], "ref"), prefixes), role))
    return frozenset(out)


def _eliminated(value: Json, prefixes: dict[str, str]) -> frozenset[tuple[str, str, str]]:
    return frozenset(
        (
            expand(as_str(e["ref"], "ref"), prefixes),
            expand(as_str(e["by"], "by"), prefixes),
            as_str(e["rule"], "rule"),
        )
        for e in (as_obj(raw, "elimination") for raw in as_list(value, "eliminated"))
    )


def _unknown_parts(value: Json, prefixes: dict[str, str]) -> frozenset[tuple[str, str, str]]:
    out: set[tuple[str, str, str]] = set()
    for raw in as_list(value, "unknown_parts"):
        p = as_obj(raw, "unknown part")
        status = as_str(p["status"], "status")
        if status not in PART_STATUSES:
            raise ValueError(f"unknown part status {status!r}")
        out.add(
            (
                expand(as_str(p["ref"], "ref"), prefixes),
                expand(as_str(p["input"], "input"), prefixes),
                status,
            )
        )
    return frozenset(out)


def _range(value: Json) -> tuple[str, str]:
    r = as_obj(value, "verdict_range")
    return (as_str(r["low"], "low"), as_str(r["high"], "high"))


def unemitted(expected: Obj, actual: Json) -> list[str]:
    """The optional fields the scenario states and the output lacks."""
    got = actual if isinstance(actual, dict) else {}
    return [k for k in OPTIONAL if k in expected and k not in got]


def mismatches(expected: Obj, actual: Json, prefixes: dict[str, str]) -> list[str]:
    """Every difference, one line each; empty means pass. A malformed output is a mismatch."""
    try:
        got = as_obj(actual, "output")
        verdict = as_str(got["verdict"], "verdict")
        if verdict not in VERDICTS:
            return [f"verdict {verdict!r} is not one of the five"]
        out: list[str] = []
        if verdict != expected["verdict"]:
            out.append(f"verdict: expected {expected['verdict']}, got {verdict}")
        want_f = _frontier(expected["frontier"], prefixes)
        got_f = _frontier(got["frontier"], prefixes)
        if want_f != got_f:
            out.append(f"frontier: expected {_show(want_f)}, got {_show(got_f)}")
        want_o = _obligations(expected["obligations"], prefixes)
        got_o = _obligations(got["obligations"], prefixes)
        if want_o != got_o:
            out.append(
                f"obligations: missing {sorted(want_o - got_o, key=str)}, "
                f"unexpected {sorted(got_o - want_o, key=str)}"
            )
        if "exact" in expected and got.get("exact") != expected["exact"]:
            out.append(f"exact: expected {expected['exact']}, got {got.get('exact')}")
        if "frontier_complete" in expected and "frontier_complete" in got:
            want_c, got_c = expected["frontier_complete"], got["frontier_complete"]
            if not isinstance(got_c, bool):
                return [f"malformed output: frontier_complete {got_c!r} is not a boolean"]
            if got_c != want_c:
                out.append(f"frontier_complete: expected {want_c}, got {got_c}")
        sets = (
            ("verdict_basis", _basis),
            ("eliminated", _eliminated),
            ("unknown_parts", _unknown_parts),
        )
        for key, read in sets:
            if key in expected and key in got:
                want: frozenset[tuple[str, ...]] = read(expected[key], prefixes)
                have: frozenset[tuple[str, ...]] = read(got[key], prefixes)
                if want != have:
                    out.append(
                        f"{key}: missing {sorted(want - have)}, unexpected {sorted(have - want)}"
                    )
        if "verdict_range" in expected and "verdict_range" in got:
            want_r = _range(expected["verdict_range"])
            got_r = _range(got["verdict_range"])
            if want_r != got_r:
                out.append(f"verdict_range: expected {want_r}, got {got_r}")
    except (TypeError, ValueError, KeyError) as e:
        return [f"malformed output: {e}"]
    return out


def _show(f: frozenset[frozenset[str]]) -> list[list[str]]:
    return sorted(sorted(alt) for alt in f)
