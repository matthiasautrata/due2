"""Compare a backend's `interpret` output with a scenario's expected result.

Output shape (spikes/README.md):
  {"verdict": str, "frontier": [[duty IRI, ...], ...],
   "obligations": [{"duty": IRI, "status": str, "instance"?: dateTime}], "exact"?: bool}

The frontier is a set of sets, obligations a set. `exact` is compared only where the
scenario states it (conformance/README.md). Prefixed names are expanded on both sides.
"""

from __future__ import annotations

from harness.json_types import Json, Obj, as_list, as_obj, as_str

VERDICTS = frozenset({"Permit", "Deny", "Pending", "NotApplicable", "Indeterminate"})
STATUSES = frozenset({"fulfilled", "outstanding", "violated", "unknown"})

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
    except (TypeError, ValueError, KeyError) as e:
        return [f"malformed output: {e}"]
    return out


def _show(f: frozenset[frozenset[str]]) -> list[list[str]]:
    return sorted(sorted(alt) for alt in f)
